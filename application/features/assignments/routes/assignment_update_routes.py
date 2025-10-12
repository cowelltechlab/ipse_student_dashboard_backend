"""
Assignment update/delete routes - PUT and DELETE operations
"""
from fastapi import Depends, HTTPException, APIRouter, status, Body

from application.features.assignments.schemas import AssignmentUpdate
from application.features.assignments.crud import (
    delete_assignment_by_id,
    update_assignment,
)
from application.features.auth.permissions import require_user_access

router = APIRouter()


@router.put("/{assignment_id}")
def update_assignment_route(
    assignment_id: int,
    data: AssignmentUpdate = Body(...),
    _user = Depends(require_user_access)
):
    """Update an assignment."""
    updated_assignment = update_assignment(assignment_id, data.dict(exclude_unset=True))
    if "error" in updated_assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=updated_assignment["error"])

    return {"success": True, "message": "Assignment updated successfully"}


@router.delete("/{assignment_id}")
def delete_assignment(
    assignment_id: int,
    _user = Depends(require_user_access)
):
    """Delete an assignment."""
    delete_assignment_by_id(assignment_id)
    return {"success": True, "message": f"Assignment with id {assignment_id} deleted."}
