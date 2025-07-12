from fastapi import HTTPException
from uuid import uuid4
from application.features.versionHistory.schemas import AssignmentVersionCreate
from datetime import datetime, timezone
from application.features.versionHistory.schemas import AssignmentVersionResponse, AssignmentVersionUpdate
from azure.cosmos import exceptions

def create_version(data: AssignmentVersionCreate, container):
    doc = data.model_dump()

    # Convert modifier_id to string for partition key
    doc["modifier_id"] = str(doc["modifier_id"])
    
    # Generate a unique ID for the new document
    doc["id"] = str(uuid4())

    # Set date_modified to now (ISO 8601 UTC)
    doc["date_modified"] = datetime.now(timezone.utc).isoformat()

    # Set finalized and starred defaults if not provided
    doc["finalized"] = doc.get("finalized", False)
    doc["starred"] = doc.get("starred", False)

    # Auto-increment version_number per assignment+modifier pair
    try:
        query = """
        SELECT VALUE MAX(c.version_number)
        FROM c
        WHERE c.assignment_id = @assignment_id AND c.modifier_id = @modifier_id
        """
        parameters = [
            {"name": "@assignment_id", "value": doc["assignment_id"]},
            {"name": "@modifier_id", "value": doc["modifier_id"]}
        ]
        results = list(container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))

        max_version = results[0] if results and results[0] is not None else 0
        doc["version_number"] = max_version + 1
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate version number: {str(e)}")
    
    # Default rating shape if missing or None
    if "rating" not in doc or doc["rating"] is None:
        doc["rating"] = {
            "difficulty": "",
            "best_changes": [],
            "disliked_changes": []
        }
    # Create the new version document in Cosmos DB
    try:
        container.create_item(body=doc)
        # Cast modifier_id back to int for the response model
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

def update_version(container, assignment_id: str, version_number: int, modifier_id: int, update_data: AssignmentVersionUpdate) -> AssignmentVersionResponse:
    # 1. Find existing version by assignment_id, version_number, AND modifier_id
    query = """
    SELECT * FROM c
    WHERE c.assignment_id = @assignment_id AND c.version_number = @version_number AND c.modifier_id = @modifier_id
    """
    params = [
        {"name": "@assignment_id", "value": assignment_id},
        {"name": "@version_number", "value": version_number},
        {"name": "@modifier_id", "value": str(modifier_id)}
    ]

    items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    
    if not items:
        raise HTTPException(status_code=404, detail="Version not found")

    existing = items[0]
    doc_id = existing["id"]

    # 2. Prepare update dict
    update_dict = update_data.dict(exclude_unset=True)

    # Convert date_modified if present and datetime
    if "date_modified" in update_dict and isinstance(update_dict["date_modified"], datetime):
        update_dict["date_modified"] = update_dict["date_modified"].isoformat()

    # Apply updates to the existing document
    for k, v in update_dict.items():
        existing[k] = v

    # Always update date_modified if content updated or explicitly (optional)
    if "content" in update_dict:
        existing["date_modified"] = datetime.now(timezone.utc).isoformat()

    try:
        # Unset finalized on others if this update finalizes this version
        if update_dict.get("finalized") is True:
            query_all = "SELECT * FROM c WHERE c.assignment_id = @assignment_id AND c.modifier_id = @modifier_id"
            params_all = [
                {"name": "@assignment_id", "value": assignment_id},
                {"name": "@modifier_id", "value": str(modifier_id)}
            ]
            all_versions = list(container.query_items(
                query=query_all,
                parameters=params_all,
                enable_cross_partition_query=True
            ))

            for v in all_versions:
                if v["id"] != doc_id and v.get("finalized"):
                    v["finalized"] = False
                    container.replace_item(item=v["id"], body=v, partition_key=str(modifier_id))

        # Save the updated document — provide partition_key!
        container.replace_item(doc_id, existing, str(modifier_id))
        existing["modifier_id"] = int(existing["modifier_id"])  # convert back for response
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

def star_assignment(container, assignment_version_id: str, starred: bool) -> AssignmentVersionResponse:
    try:
        # 1. Fetch the document by id (cross partition query)
        items = list(container.query_items(
            query="SELECT * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": assignment_version_id}],
            enable_cross_partition_query=True
        ))

        if not items:
            raise HTTPException(status_code=404, detail="Assignment version not found")

        doc = items[0]

        # 2. Update the starred field and date_modified timestamp
        doc["starred"] = starred
        doc["date_modified"] = datetime.now().astimezone().isoformat()

        # 3. Save the updated document using replace_item
        container.replace_item(item=doc["id"], body=doc)

        # 4. Convert modifier_id back to int for response model consistency
        doc["modifier_id"] = int(doc["modifier_id"])

        return AssignmentVersionResponse(**doc)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update starred status: {str(e)}")

