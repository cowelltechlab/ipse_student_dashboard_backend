from pydantic import BaseModel

class GPTRequest(BaseModel):
    prompt: str
    model: str = "gpt-5"

class GPTResponse(BaseModel):
    response: str
