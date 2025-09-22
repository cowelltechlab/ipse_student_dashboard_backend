from fastapi import APIRouter, Depends, Response
from application.database.nosql_connection import get_container
from application.features.versionHistory import crud
from application.features.versionHistory.schemas import AssignmentVersionResponse
from application.features.auth.permissions import require_user_access 

router = APIRouter()


@router.get("/assignment/{document_version_id}", response_model=AssignmentVersionResponse)
def get_assignment_version_by_document_id(
    document_version_id: str,
    user_data: dict = Depends(require_user_access)
):
    container = get_container()
    version_details = crud.get_assignment_version_by_doc_id(container, document_version_id)

    return version_details

@router.get("/assignment/download/{document_version_id}")
def download_assignment_version(
    document_version_id: str,
    user_data: dict = Depends(require_user_access)
):
    container = get_container()
    download_data = crud.download_assignment_version(container, document_version_id)
    
    return Response(
        content=download_data["file_content"],
        media_type=download_data["file_type"],
        headers={
            "Content-Disposition": f"attachment; filename=\"{download_data['file_name']}\""
        }
    )

@router.post("/assignment/finalize/{document_version_id}", response_model=AssignmentVersionResponse)
def finalize_assignment_version(
    document_version_id: str,
    user_data: dict = Depends(require_user_access)
):
    container = get_container()
    return crud.finalize_by_id(container, document_version_id, True)
