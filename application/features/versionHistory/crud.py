from azure.cosmos import ContainerProxy
from fastapi import HTTPException
from uuid import uuid4
from application.features.versionHistory.schemas import AssignmentVersionCreate
from datetime import datetime
from azure.cosmos import PartitionKey
from application.features.versionHistory.schemas import AssignmentVersionResponse, AssignmentVersionUpdate
from fastapi.responses import JSONResponse
from azure.cosmos import exceptions

def create_version(data: AssignmentVersionCreate, container):
    doc = data.model_dump()
    doc["modifier_id"] = str(doc["modifier_id"]) 
    if isinstance(doc.get("date_modified"), datetime):
        doc["date_modified"] = doc["date_modified"].isoformat()
    doc["id"] = str(uuid4())

    try:
        container.create_item(body=doc)
        # Convert back to int for response if needed
        doc["modifier_id"] = int(doc["modifier_id"])
        return AssignmentVersionResponse(**doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create version: {str(e)}")

def get_versions_by_assignment(container, assignment_id: str) -> list[AssignmentVersionResponse]:
    # Since modifier_id is partition key, but we want to query by assignment_id (not PK),
    # we must enable cross-partition query.
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
        # Step 1: Find document by assignment_id and version_number
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

        # Step 2: Delete using partition key
        container.delete_item(item=doc_id, partition_key=str(modifier_id))

    except exceptions.CosmosResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete version: {str(e)}")
    
def update_version(container, assignment_id: str, version_number: int, update_data: AssignmentVersionUpdate) -> AssignmentVersionResponse:
    # 1. Find existing document
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

    # 2. Update only fields present in update_data (exclude unset)
    update_dict = update_data.dict(exclude_unset=True)

    # 3. If date_modified present and datetime, convert to ISO string
    if "date_modified" in update_dict and isinstance(update_dict["date_modified"], datetime):
        update_dict["date_modified"] = update_dict["date_modified"].isoformat()

    for k, v in update_dict.items():
        existing[k] = v

    try:
        container.replace_item(item=doc_id, body=existing)
        # Convert back modifier_id to int for response if needed
        existing["modifier_id"] = int(existing["modifier_id"])
        return AssignmentVersionResponse(**existing)
    except exceptions.CosmosHttpResponseError as e:
        raise HTTPException(status_code=500, detail=f"Failed to update version: {str(e)}")

