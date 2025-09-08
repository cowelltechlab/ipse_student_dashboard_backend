from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from typing import Any, Dict, List, Optional
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


class GeneratedOption(BaseModel):
    model_config = ConfigDict(extra='ignore')  # ignore any unexpected fields
    name: str
    description: str
    why_good_existing: Optional[str] = None
    why_challenge: Optional[str] = None
    why_good_growth: Optional[str] = None
    selection_logic: Optional[str] = None
    internal_id: Optional[str] = None

class FinalGeneratedContent(BaseModel):
    model_config = ConfigDict(extra='ignore')
    # Your data shows: {'json_content': {...}}
    json_content: Dict[str, Any]

class AssignmentVersionResponse(BaseModel):
    # Ignore Cosmos system fields like _rid, _self, _etag, _attachments, _ts
    model_config = ConfigDict(extra='ignore', populate_by_name=True)

    id: str
    assignment_id: int
    modifier_id: int
    student_id: int
    version_number: int

    generated_options: List[GeneratedOption]
    skills_for_success: Optional[str] = None
    output_reasoning: Optional[str] = None

    finalized: bool
    date_modified: datetime

    selected_options: Optional[List[str]] = None

    # Accept both the new and old key names
    additional_edit_suggestions: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('additional_edit_suggestions', 'extra_ideas_for_changes'),
    )

    final_generated_content: Optional[FinalGeneratedContent] = None
    original_generated_json_content: Optional[Dict[str, Any]] = None


class AssignmentVersionDownloadResponse(BaseModel):
    file_name: str
    file_type: str
    file_content: bytes