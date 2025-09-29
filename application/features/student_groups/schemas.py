
from typing import Optional
from pydantic import BaseModel


class StudentDetailsResponse(BaseModel):
    student_id: int
    first_name: str
    last_name: str
    email: Optional[str]
    gt_email: Optional[str]
    profile_picture_url: Optional[str]
    group_type: Optional[str]
    ppt_embed_url: Optional[str]
    ppt_edit_url: Optional[str]

    class Config:
        from_attributes = True

class StudentGroupTypeUpdate(BaseModel):
    group_type: Optional[str] = None

class StudentPptUrlsUpdate(BaseModel):
    ppt_embed_url: Optional[str] = None
    ppt_edit_url: Optional[str] = None

class StudentEmailUpdate(BaseModel):
    email: Optional[str] = None
    gt_email: Optional[str] = None