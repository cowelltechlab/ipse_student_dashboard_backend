from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime



class UDLReasons(BaseModel):
    Engagement: Optional[str] = None
    Expression: Optional[str] = None
    Representation: Optional[str] = None

class GeneratedOption(BaseModel):
    title: str
    description: str
    reasons: List[str]


class AssignmentVersionBase(BaseModel):
    assignment_id: str
    version_number: int
    modifier_id: int  
    date_modified: datetime
    content: Optional[str] = None
    udl_reasons: Optional[UDLReasons] = None
    finalized: Optional[bool] = False
    starred: Optional[bool] = False
    generated_options: Optional[List[GeneratedOption]] = None


class AssignmentVersionResponse(AssignmentVersionBase):
    id: str

class AssignmentVersionUpdate(BaseModel):
    content: Optional[str] = None
    udl_reasons: Optional[UDLReasons] = None
    finalized: Optional[bool] = None
    starred: Optional[bool] = None
    date_modified: Optional[datetime] = None

class GeneratedOption(BaseModel):
    name: str
    description: str
    why_good_existing: str
    why_good_growth: str
    internal_id: Optional[str]


class FinalGeneratedContent(BaseModel):
    html_content: str


class AssignmentVersionResponse(BaseModel):
    id: str
    assignment_id: int
    modifier_id: int
    student_id: int
    version_number: int
    generated_options: List[GeneratedOption]
    skills_for_success: Optional[str]
    finalized: bool
    date_modified: str
    selected_options: Optional[List[str]]
    extra_ideas_for_changes: Optional[str]
    final_generated_content: Optional[FinalGeneratedContent]
