from typing import List, Optional
from pydantic import BaseModel, EmailStr


class InviteUserRequest(BaseModel):
    school_email: EmailStr
    google_email: Optional[EmailStr]
    role_ids: List[int]
    student_type: Optional[str] = None

class CompleteInviteRequest(BaseModel):
    token: str
    first_name: Optional[str]
    last_name: Optional[str]
    password: str
    profile_picture_url: Optional[str]

class DefaultProfilePicture(BaseModel):
    id: int
    url: str
    
    class Config:
        orm_mode = True