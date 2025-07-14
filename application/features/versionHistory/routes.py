from fastapi import APIRouter, status, Depends
from application.database.nosql_connection import get_container
from application.features.versionHistory import crud
from application.features.versionHistory.schemas import AssignmentVersionCreate, AssignmentVersionResponse, AssignmentVersionUpdate, FinalizeVersionRequest, StarVersionRequest
from application.features.auth.permissions import require_user_access 

router = APIRouter()

@router.post("/{assignment_id}", response_model=AssignmentVersionResponse, status_code=status.HTTP_201_CREATED)
def create_version(
    assignment_id: str,
    version: AssignmentVersionCreate,
    user_data: dict = Depends(require_user_access)
):
    container = get_container()
    return crud.create_version(assignment_id, version, container)

@router.get("/{assignment_id}", response_model=list[AssignmentVersionResponse])
def list_versions_by_assignment(
    assignment_id: str,
    user_data: dict = Depends(require_user_access)
):
    container = get_container()
    return crud.get_versions_by_assignment(container, assignment_id)

@router.get("/{assignment_id}/version/{version_number}", response_model=AssignmentVersionResponse)
def get_specific_version(
    assignment_id: str,
    version_number: int,
    user_data: dict = Depends(require_user_access)
):
    container = get_container()
    return crud.get_version(container, assignment_id, version_number)

@router.delete("/{assignment_id}/version/{version_number}", status_code=status.HTTP_204_NO_CONTENT)
def delete_version_by_assignment_version(
    assignment_id: str,
    version_number: int,
    user_data: dict = Depends(require_user_access)
):
    container = get_container()
    crud.delete_version_by_assignment_version(container, assignment_id, version_number)
    return None

@router.put("/{assignment_id}/version/{version_number}/modifier/{modifier_id}", response_model=AssignmentVersionResponse)
def update_version_route(
    assignment_id: str,
    version_number: int,
    modifier_id: int,
    update_data: AssignmentVersionUpdate,
    user_data: dict = Depends(require_user_access)
):
    """
    Update content of a version document, and refresh date_modified.
    """
    container = get_container()
    return crud.update_version(container, assignment_id, version_number, modifier_id, update_data)

@router.post("/finalize/{assignment_version_id}", response_model=AssignmentVersionResponse)
def finalize_assignment_version(
    assignment_version_id: str,
    request: FinalizeVersionRequest,
    user_data: dict = Depends(require_user_access)
):
    container = get_container()
    return crud.finalize_by_id(container, assignment_version_id, request.finalized, user_data)

@router.post("/star/{assignment_version_id}", response_model=AssignmentVersionResponse)
def finalize_assignment_version(
    assignment_version_id: str,
    request: StarVersionRequest,
    user_data: dict = Depends(require_user_access)
):
    container = get_container()
    return crud.star_assignment(container, assignment_version_id, request.starred)
