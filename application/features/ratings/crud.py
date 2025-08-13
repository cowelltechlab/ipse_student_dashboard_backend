
import datetime
from fastapi import HTTPException
from application.features.ratings.schemas import RatingUpdateRequest
from application.features.versionHistory.schemas import AssignmentVersionResponse


def get_rating_data_by_assignment_version_id(assignment_version_id: str) -> AssignmentRatingData:
    

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

