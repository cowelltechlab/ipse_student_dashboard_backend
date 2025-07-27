from fastapi import APIRouter, Depends, HTTPException
from application.database.nosql_connection import get_cosmos_db_connection
from application.features.assignment_version_generation.crud import handle_assignment_suggestion_generation
from application.features.auth.permissions import require_user_access


from application.features.assignment_version_generation.schemas import AssignmentGenerationOptionsResponse

router = APIRouter()
DATABASE_NAME = "ai-prompt-storage"
CONTAINER_NAME = "ai-modified-assignments"
cosmos_client = get_cosmos_db_connection()
cosmos_container = cosmos_client.get_database_client(DATABASE_NAME).get_container_client(CONTAINER_NAME)


@router.get("/assignment-generation/{assignment_id}", response_model=AssignmentGenerationOptionsResponse)
def generate_assignment_options(assignment_id: int, _user=Depends(require_user_access)):
    
    return handle_assignment_suggestion_generation(assignment_id, _user["user_id"])
