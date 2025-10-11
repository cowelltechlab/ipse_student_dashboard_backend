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
    assignment_type_id: Optional[int] = None


class AssignmentListResponse(AssignmentBase):
    blob_url: Optional[str] = None
    source_format: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    # Return NoSQL Fields
    finalized: Optional[bool] = None
    rating_status: Optional[str] = None
    final_version_id: Optional[str] = None
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
    final_version_id: Optional[str] = None  # ID of the finalized version
    rating_status: Optional[str] = None    # Overall rating status
    versions: List[VersionInfo] = []

    class Config:
        from_attributes = True

class AssignmentCreateResponse(BaseModel):
    id: int
    student_id: int
    title: str
    class_id: int
    content: str
    date_created: datetime
    blob_url: Optional[str] = None
    source_format: Optional[str] = None
    hyperlink: Optional[str] = None
    assignment_type_id: Optional[int] = None


class AssignmentTypeListResponse(BaseModel):
    id: int
    type: str


class AssignmentTextCreate(BaseModel):
    student_id: int
    title: str
    class_id: int
    content: str
    assignment_type_id: Optional[int] = None
    date_created: Optional[datetime] = None


class AssignmentTextBulkCreate(BaseModel):
    student_ids: List[int]
    title: str
    class_id: int
    content: str
    assignment_type_id: Optional[int] = None


# Export Schemas
class StudentInfoExport(BaseModel):
    id: int
    user_id: int
    first_name: str
    last_name: str
    email: Optional[str] = None
    gt_email: Optional[str] = None
    year_name: Optional[str] = None
    reading_level: Optional[str] = None
    writing_level: Optional[str] = None
    group_type: Optional[str] = None


class ClassAssociationExport(BaseModel):
    class_id: int
    class_name: str
    course_code: Optional[str] = None
    term: Optional[str] = None
    type: Optional[str] = None
    learning_goal: Optional[str] = None


class AssignmentVersionExport(BaseModel):
    """Complete version document from Cosmos DB"""
    id: str
    assignment_id: int
    version_number: Optional[int] = None
    modifier_id: Optional[int] = None
    student_id: Optional[int] = None
    finalized: Optional[bool] = False
    date_modified: Optional[str] = None
    generated_options: Optional[List[dict]] = None
    selected_options: Optional[List[str]] = None
    skills_for_success: Optional[str] = None
    output_reasoning: Optional[str] = None
    final_generated_content: Optional[dict] = None
    original_generated_content: Optional[dict] = None
    generation_history: Optional[List[dict]] = None
    rating_data: Optional[dict] = None
    rating_history: Optional[List[dict]] = None
    additional_edit_suggestions: Optional[str] = None


class AssignmentExport(BaseModel):
    assignment_id: int
    title: str
    content: str
    html_content: Optional[str] = None
    date_created: datetime
    blob_url: Optional[str] = None
    source_format: Optional[str] = None
    assignment_type: Optional[str] = None
    assignment_type_id: Optional[int] = None
    class_info: Optional[ClassInfo] = None
    versions: List[AssignmentVersionExport] = []


class StudentAssignmentExportResponse(BaseModel):
    student: StudentInfoExport
    classes: List[ClassAssociationExport]
    assignments: List[AssignmentExport]
    export_metadata: dict