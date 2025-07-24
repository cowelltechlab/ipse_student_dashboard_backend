from azure.cosmos import ContainerProxy
from fastapi import HTTPException
from uuid import uuid4
from application.features.versionHistory.schemas import AssignmentVersionCreate, RatingUpdateRequest
from datetime import datetime
from azure.cosmos import PartitionKey
from application.features.versionHistory.schemas import AssignmentVersionResponse, AssignmentVersionUpdate
from fastapi.responses import JSONResponse
from azure.cosmos import exceptions

def create_version(data: AssignmentVersionCreate, container):
    doc = data.model_dump()
    doc["modifier_id"] = str(doc["modifier_id"]) 
    doc["id"] = str(uuid4())

    if isinstance(doc.get("date_modified"), datetime):
        doc["date_modified"] = doc["date_modified"].isoformat()

    # If this version is being finalized, unset all others for this assignment
    if doc.get("finalized"):
        # Fetch all previous versions of the assignment
        query = "SELECT * FROM c WHERE c.assignment_id = @assignment_id"
        parameters = [{"name": "@assignment_id", "value": doc["assignment_id"]}]
        existing_versions = list(container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))

        for version in existing_versions:
            if version.get("finalized"):
                version["finalized"] = False
                try:
                    container.replace_item(item=version["id"], body=version)
                except Exception as e:
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Failed to unset finalized on previous version {version['version_number']}: {str(e)}"
                    )

    # Create the new version
    try:
        container.create_item(body=doc)
        # Cast modifier_id back to int for response
        doc["modifier_id"] = int(doc["modifier_id"])
        return AssignmentVersionResponse(**doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create version: {str(e)}")

def get_versions_by_assignment(container, assignment_id: str) -> list[AssignmentVersionResponse]:
    # Since modifier_id is partition key, but we want to query by assignment_id (not PK),
    # need to cross-partition query.
    query = "SELECT * FROM c WHERE c.assignment_id = @assignment_id"
    parameters = [{"name": "@assignment_id", "value": assignment_id}]

    try:
        items = list(container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        return [AssignmentVersionResponse(**item) for item in items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch versions: {str(e)}")

def get_version(container, assignment_id: str, version_number: int) -> AssignmentVersionResponse:
    query = ("SELECT * FROM c WHERE c.assignment_id = @assignment_id AND c.version_number = @version_number")
    parameters = [
        {"name": "@assignment_id", "value": assignment_id},
        {"name": "@version_number", "value": version_number}
    ]

    try:
        items = list(container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        if not items:
            raise HTTPException(status_code=404, detail="Version not found")
        return AssignmentVersionResponse(**items[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch version: {str(e)}")

def delete_version_by_assignment_version(container, assignment_id: str, version_number: int):
    try:
        # 1. Find document by assignment_id and version_number
        query = """
        SELECT * FROM c 
        WHERE c.assignment_id = @assignment_id AND c.version_number = @version_number
        """
        params = [
            {"name": "@assignment_id", "value": assignment_id},
            {"name": "@version_number", "value": version_number}
        ]
        items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

        if not items:
            raise HTTPException(status_code=404, detail="Document not found")

        item = items[0]
        doc_id = item["id"]
        modifier_id = item["modifier_id"]

        #2.  Delete using partition key
        container.delete_item(item=doc_id, partition_key=str(modifier_id))

    except exceptions.CosmosResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete version: {str(e)}")

def update_version(container, assignment_id: str, version_number: int, update_data: AssignmentVersionUpdate) -> AssignmentVersionResponse:
    # 1. Find existing version
    query = """
    SELECT * FROM c
    WHERE c.assignment_id = @assignment_id AND c.version_number = @version_number
    """
    params = [
        {"name": "@assignment_id", "value": assignment_id},
        {"name": "@version_number", "value": version_number}
    ]
    items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    
    if not items:
        raise HTTPException(status_code=404, detail="Version not found")

    existing = items[0]
    doc_id = existing["id"]
    partition_key = existing["modifier_id"]

    # 2. Prepare the update
    update_dict = update_data.dict(exclude_unset=True)

    # Convert date_modified if provided
    if "date_modified" in update_dict and isinstance(update_dict["date_modified"], datetime):
        update_dict["date_modified"] = update_dict["date_modified"].isoformat()

    # Apply updates to existing doc
    for k, v in update_dict.items():
        existing[k] = v

    try:
        # If this update sets finalized=True, unset others
        if update_dict.get("finalized") is True:
            # Find all versions for this assignment
            query_all = "SELECT * FROM c WHERE c.assignment_id = @assignment_id"
            params_all = [{"name": "@assignment_id", "value": assignment_id}]
            all_versions = list(container.query_items(
                query=query_all,
                parameters=params_all,
                enable_cross_partition_query=True
            ))

            for v in all_versions:
                if v["id"] != doc_id and v.get("finalized"):
                    v["finalized"] = False
                    container.replace_item(item=v["id"], body=v)

        # Save the current version
        container.replace_item(item=doc_id, body=existing)
        existing["modifier_id"] = int(existing["modifier_id"])
        return AssignmentVersionResponse(**existing)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update version: {str(e)}")
    
def finalize_by_id(container, assignment_version_id: str, finalized: bool) -> AssignmentVersionResponse:
    # Step 1: Get the current document by ID
    try:
        items = list(container.query_items(
            query="SELECT * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": assignment_version_id}],
            enable_cross_partition_query=True
        ))

        if not items:
            raise HTTPException(status_code=404, detail="Assignment version not found")

        current = items[0]
        assignment_id = current["assignment_id"]
        current["finalized"] = finalized
        container.replace_item(item=current["id"], body=current)

        # Step 2: If setting to True, un-finalize all others
        if finalized:
            others = list(container.query_items(
                query="""
                SELECT * FROM c 
                WHERE c.assignment_id = @assignment_id AND c.id != @id
                """,
                parameters=[
                    {"name": "@assignment_id", "value": assignment_id},
                    {"name": "@id", "value": assignment_version_id}
                ],
                enable_cross_partition_query=True
            ))

            for item in others:
                if item.get("finalized") is True:
                    item["finalized"] = False
                    container.replace_item(item=item["id"], body=item)

        # Return updated
        current["modifier_id"] = int(current["modifier_id"])
        return AssignmentVersionResponse(**current)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to finalize version: {str(e)}")

def update_rating_fields(
    container,
    assignment_id: str,
    version_number: int,
    modifier_id: str,
    update_data: RatingUpdateRequest
) -> AssignmentVersionResponse:
    # Find the existing version using all three filters

    print("Querying CosmosDB with:")
    print(f"assignment_id: {assignment_id} ({type(assignment_id)})")
    print(f"version_number: {version_number} ({type(version_number)})")
    print(f"modifier_id: {modifier_id} ({type(modifier_id)})")

    query = """
    SELECT * FROM c 
    WHERE c.assignment_id = @assignment_id 
      AND c.version_number = @version_number 
      AND c.modifier_id = @modifier_id
    """
    params = [
        {"name": "@assignment_id", "value": assignment_id},
        {"name": "@version_number", "value": version_number},
        {"name": "@modifier_id", "value": modifier_id}
    ]
    

    items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

    if not items:
        raise HTTPException(status_code=404, detail="Version not found")
    
    print("Returned items:", items)


    existing = items[0]
    doc_id = existing["id"]
    partition_key = existing["modifier_id"]

    update_dict = update_data.dict(exclude_unset=True)

    # Optional: ISO format datetime
    if "date_modified" in update_dict and isinstance(update_dict["date_modified"], datetime):
        update_dict["date_modified"] = update_dict["date_modified"].isoformat()

    for key, value in update_dict.items():
        existing[key] = value

    try:
        container.replace_item(item=doc_id, body=existing)
        existing["modifier_id"] = int(existing["modifier_id"])
        return AssignmentVersionResponse(**existing)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update rating info: {str(e)}")

