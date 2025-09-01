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
        from_attributes = True


class StudentInfo(BaseModel):
    id: int
    first_name: str
    last_name: str

class ClassInfo(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    course_code: Optional[str] = None

class VersionInfo(BaseModel):
    document_id: str
    version_number: Optional[int] = None
    modified_by: Optional[str] = None     # User name
    modifier_role: Optional[str] = None   # Role name
    date_modified: Optional[datetime] = None
    document_url: Optional[str] = None
    finalized: Optional[bool] = None
    rating_status: Optional[str] = None


class AssignmentDetailResponse(BaseModel):
    # Assignment Core Fields
    assignment_id: int
    title: str
    content: str
    date_created: datetime
    blob_url: Optional[str] = None
    source_format: Optional[str] = None
    html_content: Optional[str] = None
    assignment_type: Optional[str] = None
    assignment_type_id: Optional[int] = None

    # Nested Info
    student: StudentInfo
    class_info: Optional[ClassInfo] = None

    # Version Information
    finalized: Optional[bool] = None       # Overall: any version is finalized
    rating_status: Optional[str] = None    # Overall rating status
    versions: List[VersionInfo] = []

    class Config:
        from_attributes = True


class AssignmentTypeListResponse(BaseModel):
    id: int
    type: str