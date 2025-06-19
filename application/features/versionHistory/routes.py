from fastapi import APIRouter, Depends, HTTPException # Assume this gives Cosmos container
from application.database.nosql_connection import get_container
from application.features.versionHistory.crud import get_all_versions, get_version, create_or_append_version, update_version, delete_version
from application.features.versionHistory.schemas import AssignmentVersionBase, AssignmentVersionCreate, AssignmentVersionResponse, AssignmentVersionUpdate

router = APIRouter()

@router.post("/{student_id}/{assignment_id}/versions", response_model=AssignmentVersionResponse, status_code=201)
def create_version(student_id: int, assignment_id: str, version: AssignmentVersionCreate, container=Depends(get_container)):
    try:
        print(f"Received data: {version}")
        doc = create_or_append_version(container, student_id, assignment_id, version)
        print(f"Document after create_or_append_version: {doc}")
        added_version = next(
            (v for v in doc.get("versions", []) if v["version_number"] == version.version_number),
            None
        )
        if not added_version:
            raise HTTPException(status_code=500, detail="Failed to add version")
        return added_version
    except Exception as e:
        print(f"Exception in create_version: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{student_id}/{assignment_id}/versions", response_model=list[AssignmentVersionResponse])
def list_versions(student_id: int, assignment_id: str, container=Depends(get_container)):
    return get_all_versions(container, student_id, assignment_id)

@router.get("/{student_id}/{assignment_id}/versions/{version_number}", response_model=AssignmentVersionResponse)
def get_version_route(student_id: int, assignment_id: str, version_number: int, container=Depends(get_container)):
    try:
        return get_version(container, student_id, assignment_id, version_number)
    except Exception:
        raise HTTPException(status_code=404, detail="Version not found")

@router.put("/{student_id}/{assignment_id}/versions/{version_number}", response_model=AssignmentVersionResponse)
def update_version_route(student_id: int, assignment_id: str, version_number: int, update: AssignmentVersionUpdate, container=Depends(get_container)):
    return update_version(container, student_id, assignment_id, version_number, update)

@router.delete("/{student_id}/{assignment_id}/versions/{version_number}", status_code=204)
def delete_version_route(student_id: int, assignment_id: str, version_number: int, container=Depends(get_container)):
    delete_version(container, student_id, assignment_id, version_number)
