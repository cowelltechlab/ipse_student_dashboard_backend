
from typing import Optional
from pydantic import BaseModel


class Role(BaseModel):
    id: int
    role_name: str
    description: str

class RoleCreate(BaseModel):
    role_name: str
    description: str

class RoleUpdate(BaseModel):
    role_name: Optional[str] = None
    description: Optional[str] = None

class RoleResponse(BaseModel):
    id: int
    role_name: str
    description: str

    class Config:
        from_attributes = True