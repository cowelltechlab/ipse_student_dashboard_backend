from typing import List, Optional
from pydantic import BaseModel, EmailStr


class InviteUserRequest(BaseModel):
    school_email: EmailStr
    google_email: Optional[EmailStr]
    role_ids: List[int]

class CompleteInviteRequest(BaseModel):
    token: str
    first_name: str
    last_name: str
    password: str
    profile_picture_url: Optional[str]
