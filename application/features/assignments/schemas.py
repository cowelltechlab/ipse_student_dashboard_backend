from pydantic import BaseModel
from typing import Optional, List
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
    html_content: Optional[str] = None
    blob_url: Optional[str] = None
    source_format: Optional[str] = None
    date_created: Optional[datetime] = None
    assignment_type_id: Optional[int] = None


class AssignmentUpdate(BaseModel):
    student_id: Optional[int] = None
    title: Optional[str] = None
    class_id: Optional[int] = None
    content: Optional[str] = None
    date_created: Optional[datetime] = None

# Updated Assignment List Response with issue#50 requirements
class AssignmentListResponse(AssignmentBase):
    blob_url: Optional[str] = None
    source_format: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    # Return NoSQL Fields
    finalized: Optional[bool] = None
    rating_status: Optional[str] = None
    date_modified: Optional[datetime] = None

    class Config:
        orm_mode = True


class AssignmentDetailResponse(AssignmentBase):
    content: str
    blob_url: Optional[str] = None
    source_format: Optional[str] = None
    html_content: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    assignment_type_id: Optional[int] = None

    # Return NoSQL Fields
    finalized: Optional[bool] = None
    rating_status: Optional[str] = None
    date_modified: Optional[datetime] = None

    class Config:
        orm_mode = True


class AssignmentTypeListResponse(BaseModel):
    id: int
    type: str