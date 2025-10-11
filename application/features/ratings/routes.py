

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends

from application.features.auth.permissions import require_user_access
from application.features.ratings.crud import (
    get_rating_data_by_assignment_version_id,
    upsert_rating_fields,
    get_existing_rating_data,
    get_rating_history
)
from application.features.ratings.schemas import (
    AssignmentRatingData,
    RatingUpdateRequest,
    RatingUpdateResponse,
    ExistingRatingDataResponse,
    RatingHistoryResponse
)


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


@router.get("/{assignment_version_id}/data", response_model=ExistingRatingDataResponse)
def get_existing_assignment_rating_data(
    assignment_version_id: str,
    user_data: dict = Depends(require_user_access)
):
    """
    Retrieves existing rating responses for a specific assignment version.
    Returns 404 if no rating data exists.
    """
    rating_data = get_existing_rating_data(assignment_version_id)
    return rating_data


@router.get("/{assignment_version_id}/history", response_model=RatingHistoryResponse)
def get_assignment_rating_history(
    assignment_version_id: str,
    user_data: dict = Depends(require_user_access)
):
    """
    Retrieves the complete rating history for an assignment version.
    Includes current rating data and all historical snapshots from previous updates.
    """
    history_data = get_rating_history(assignment_version_id)
    return history_data