from fastapi import APIRouter, HTTPException, status
from application.database.nosql_connection import get_container
from application.features.versionHistory import crud
from application.features.versionHistory.schemas import AssignmentVersionCreate, AssignmentVersionResponse

router = APIRouter()

@router.post("/", response_model=AssignmentVersionResponse, status_code=status.HTTP_201_CREATED)
def create_version(version: AssignmentVersionCreate):
    container = get_container()  # gets the actual container client
    return crud.create_version(version, container)

@router.get("/assignment/{assignment_id}", response_model=list[AssignmentVersionResponse])
def list_versions_by_assignment(assignment_id: str):
    container = get_container()
    return crud.get_versions_by_assignment(container, assignment_id)


@router.get("/assignment/{assignment_id}/version/{version_number}", response_model=AssignmentVersionResponse)
def get_specific_version(assignment_id: str, version_number: int):
    container = get_container()
    return crud.get_version(container, assignment_id, version_number)


@router.delete("/assignment/{assignment_id}/version/{version_number}", status_code=status.HTTP_204_NO_CONTENT)
def delete_version_by_assignment_version(assignment_id: str, version_number: int):
    container = get_container()
    crud.delete_version_by_assignment_version(container, assignment_id, version_number)
    return None