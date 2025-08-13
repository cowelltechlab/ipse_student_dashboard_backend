from fastapi import APIRouter, Depends, HTTPException

from application.features.student_profile.crud import get_profile
from .schemas import GPTRequest, GPTResponse
from .crud import generate_gpt_prompt, process_gpt_prompt
from datetime import datetime
from application.features.auth.permissions import require_user_access
from application.features.assignments.crud import get_assignment_by_id
from application.features.students.crud import get_student_by_student_id
from application.features.versionHistory.schemas import AssignmentVersionResponse
from application.features.gpt.crud import process_gpt_prompt

router = APIRouter()

@router.post("/chat", response_model=GPTResponse)
async def chat_endpoint(
    request: GPTRequest,
    user_data: dict = Depends(require_user_access)
):
    try:
        answer = process_gpt_prompt(request.prompt, request.model)
        return GPTResponse(response=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
