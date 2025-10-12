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
        from_attributes = True

class UserEmailUpdateData(BaseModel):
    email: Optional[str] = None
    gt_email: Optional[str] = None


class UserNameUpdateData(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserDetailsResponse(BaseModel):
    student_id: Optional[int] = None
    user_id: int
    first_name: str
    last_name: str
    email: Optional[str] = None
    gt_email: Optional[str] = None
    profile_picture_url: Optional[str] = None
    group_type: Optional[str] = None
    ppt_embed_url: Optional[str] = None
    ppt_edit_url: Optional[str] = None

    class Config:
        from_attributes = True
