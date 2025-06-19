from typing import List, Optional
from pydantic import BaseModel


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    school_email: str
    email: Optional[str]
    roles: Optional[List[str]] 
    role_ids: Optional[List[int]]


class Role(BaseModel):
    id: int
    role_name: str
    description: str