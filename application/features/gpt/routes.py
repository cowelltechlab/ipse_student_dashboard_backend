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


# @router.post("/assignments/{assignment_id}/generate-version/{student_id}", response_model=AssignmentVersionResponse)
# def generate_assignment_version(
#     assignment_id: str,
#     student_id: str,
#     user_data: dict = Depends(require_user_access)
# ):
#     # 1. Get original assignment
#     assignment = get_assignment_by_id(assignment_id)
#     if not assignment:
#         raise HTTPException(status_code=404, detail="Assignment not found")

#     # 2. Get student metadata
#     student = get_student_by_student_id(student_id)
#     if not student:
#         raise HTTPException(status_code=404, detail="Student not found")

#     # 3. Get student profile
#     profile = get_profile(student_id)
#     if not profile:
#         raise HTTPException(status_code=404, detail="Student profile not found")

#     # 4. Construct GPT prompt
#     prompt = generate_gpt_prompt(
#         assignment=assignment,
#         student=student,
#         profile=profile
#     )

#     # 5. Call GPT to get modified content
#     try:
#         modified_html = process_gpt_prompt(prompt)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"GPT generation failed: {str(e)}")