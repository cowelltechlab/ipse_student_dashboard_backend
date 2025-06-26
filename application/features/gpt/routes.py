from fastapi import APIRouter, HTTPException
from .schemas import GPTRequest, GPTResponse
from .crud import process_gpt_prompt

router = APIRouter()

@router.post("/chat", response_model=GPTResponse)
async def chat_endpoint(request: GPTRequest):
    try:
        answer = process_gpt_prompt(request.prompt, request.model)
        return GPTResponse(response=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
