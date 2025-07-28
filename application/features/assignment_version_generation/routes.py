from typing import List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException
from application.database.nosql_connection import get_cosmos_db_connection
from application.features.assignment_version_generation.crud import handle_assignment_suggestion_generation, handle_assignment_version_generation, handle_assignment_version_update
from application.features.auth.permissions import require_user_access


from application.features.assignment_version_generation.schemas import AssignmentGenerationOptionsResponse, AssignmentVersionGenerationResponse

router = APIRouter()
DATABASE_NAME = "ai-prompt-storage"
CONTAINER_NAME = "ai-modified-assignments"
cosmos_client = get_cosmos_db_connection()
cosmos_container = cosmos_client.get_database_client(DATABASE_NAME).get_container_client(CONTAINER_NAME)


@router.get("/assignment-generation/{assignment_id}", response_model=AssignmentGenerationOptionsResponse)
def generate_assignment_options(assignment_id: int, _user=Depends(require_user_access)):
    
    return handle_assignment_suggestion_generation(assignment_id, _user["user_id"])


@router.post("/assignment-generation/{assignment_version_id}", response_model=AssignmentVersionGenerationResponse)
def generate_new_assignment_version(
    assignment_version_id: str,
    selected_options: List[str] = Body(...),
    additional_edit_suggestions: Optional[str] = Body("")
):
    return handle_assignment_version_generation(
        assignment_version_id,
        selected_options,
        additional_edit_suggestions or ""
    )
    

@router.put("/assignment-generation/{assignment_version_id}", response_model=AssignmentVersionGenerationResponse)
def update_assignment_version(
    assignment_version_id: str,
    updated_html_content: str = Body(...),
    _user=Depends(require_user_access)
):
    """
    Updates the assignment and saves the original version under original_version in cosmos
    """
    return handle_assignment_version_update(assignment_version_id, updated_html_content)