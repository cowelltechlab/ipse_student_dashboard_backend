from pydantic import BaseModel

class GPTRequest(BaseModel):
    prompt: str
    model: str = "gpt-3.5-turbo"

class GPTResponse(BaseModel):
    response: str
