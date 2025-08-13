from pydantic import BaseModel, Field, validator
from typing import Any, Dict, List, Optional

class LearningPathwayOption(BaseModel):
    name: str
    description: str
    why_good_existing: str
    why_challenge: str
    why_good_growth: str
    selection_logic: str
    internal_id: str

class AssignmentGenerationRequest(BaseModel):
    selected_options: List[str] = Field(..., description="Array of option identifiers (strings).", min_items=0)
    additional_edit_suggestions: Optional[str] = Field(
        default="",
        description="Optional free-text ideas to apply."
    )

    @validator("selected_options", pre=True)
    def _normalize_ids(cls, v):
        # Accept numbers or strings; store as strings
        return [str(x) for x in (v or [])]

class AssignmentVersionGenerationResponse(BaseModel):
    version_document_id: str
    json_content: dict  # your validated, ordered JSON object


class AssignmentGenerationOptionsResponse(BaseModel):
    skills_for_success: str
    learning_pathways: List[LearningPathwayOption]
    version_document_id: str


class AssignmentVersionGenerationResponse(BaseModel):
    version_document_id: str
    json_content: Dict[str, Any]

class AssignmentUpdateBody(BaseModel):
    updated_json_content: dict
    output_reasoning: str