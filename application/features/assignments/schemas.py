from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AssignmentBase(BaseModel):
    id: Optional[int] = None
    student_id: int
    title: str
    class_id: int
    date_created: Optional[datetime] = None

class AssignmentCreate(BaseModel):
    student_id: int
    title: str
    class_id: int
    content: str
    assignment_type_id: int
    html_content: Optional[str] = None
    blob_url: Optional[str] = None
    source_format: Optional[str] = None
    date_created: Optional[datetime] = None

class AssignmentUpdate(BaseModel):
    student_id: Optional[int] = None
    title: Optional[str] = None
    class_id: Optional[int] = None
    content: Optional[str] = None
    assignment_type_id: Optional[int] = None
    date_created: Optional[datetime] = None

class AssignmentListResponse(AssignmentBase):
    blob_url: Optional[str] = None
    source_format: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    class Config:
        orm_mode = True


class AssignmentDetailResponse(AssignmentBase):
    content: str
    blob_url: Optional[str] = None
    source_format: Optional[str] = None
    html_content: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    class Config:
        orm_mode = True
