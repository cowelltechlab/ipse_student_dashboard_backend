

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends

from application.features.auth.permissions import require_user_access
from application.features.ratings.crud import get_rating_data_by_assignment_version_id, upsert_rating_fields
from application.features.ratings.schemas import AssignmentRatingData, RatingUpdateRequest, RatingUpdateResponse


router = APIRouter()


@router.get("/{assignment_version_id}", response_model=AssignmentRatingData)
def get_assignment_rating_data(
    assignment_version_id: str,
    user_data: dict = Depends(require_user_access)
):
    """
    Fetches rating data for a specific assignment version
    """
    rating_data = get_rating_data_by_assignment_version_id(assignment_version_id)

    if not rating_data:
        raise HTTPException(status_code=404, detail="Assignment version not found or no ratings available")

    return rating_data



@router.post("/{assignment_version_id}", response_model=RatingUpdateResponse)
def post_version_rating(
    assignment_version_id: str,
    rating_data: RatingUpdateRequest,
    user_data: dict = Depends(require_user_access)
):
    """
    Posts rating data for assignment version
    """
    response = upsert_rating_fields(assignment_version_id, rating_data)

    if not response or not response.get("success"):
        raise HTTPException(status_code=500, detail="Failed to save rating data")

    return RatingUpdateResponse(
        success=response["success"],
        assignment_version_id=response["assignment_version_id"],
        message=response["message"],
        last_rating_update=response["rating_data"]["last_rating_update"]
    )