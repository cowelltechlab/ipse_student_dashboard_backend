from pydantic import BaseModel, Field, field_validator, model_validator, root_validator, validator
from typing import Any, Dict, List, Optional

class LearningPathwayOption(BaseModel):
    name: str
    description: str
    why_good_existing: str
    why_challenge: str
    why_good_growth: str
    selection_logic: str
    internal_id: str
    selected: bool = False

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


class AssignmentGenerationOptionsResponse(BaseModel):
    skills_for_success: str
    learning_pathways: List[LearningPathwayOption]
    version_document_id: str


class AssignmentVersionGenerationResponse(BaseModel):
    version_document_id: str
    html_content: str


class SupportToolsModel(BaseModel):
    toolsHtml: str
    aiPromptingHtml: str
    aiPolicyHtml: str

    class Config:
        extra = "forbid"

class AssignmentJsonContent(BaseModel):
    assignmentInstructionsHtml: str
    stepByStepPlanHtml: str
    promptsHtml: str
    supportTools: SupportToolsModel
    motivationalMessageHtml: str

    class Config:
        extra = "forbid"

    @staticmethod
    def _is_fragment(s: str) -> bool:
        if not isinstance(s, str):
            return False
        sl = s.lower()
        return all(tag not in sl for tag in ("<html", "<body", "<head", "<!doctype"))

    # Prefer field_validator in v2 (mode="before" replaces pre=True)
    @field_validator("assignmentInstructionsHtml", "stepByStepPlanHtml",
                     "promptsHtml", "motivationalMessageHtml")
    def _html_fragments(cls, v: str):
        if not AssignmentJsonContent._is_fragment(v):
            raise ValueError("Must be an HTML fragment without outer wrappers")
        return v

    @model_validator(mode="after")
    def _support_tools_fragments(self):
        st = self.supportTools
        if st:
            for k in ("toolsHtml", "aiPromptingHtml", "aiPolicyHtml"):
                if not self._is_fragment(getattr(st, k)):
                    raise ValueError(f"supportTools.{k} must be an HTML fragment without outer wrappers")
        return self


class AssignmentUpdateBody(BaseModel):
    updated_html_content: str = Field(..., description="Full assignment HTML content.")

class SupportTools(BaseModel):
    toolsHtml: str
    aiPromptingHtml: str
    aiPolicyHtml: str

class AssignmentJson(BaseModel):
    assignmentInstructionsHtml: str
    stepByStepPlanHtml: str
    promptsHtml: str
    supportTools: SupportTools
    motivationalMessageHtml: str

# Legacy JSON-based schemas (kept for backward compatibility)
class AssignmentVersionGenerationJsonResponse(BaseModel):
    """Legacy response model - use AssignmentVersionGenerationResponse instead"""
    version_document_id: str
    json_content: Dict[str, Any]

class AssignmentUpdateJsonBody(BaseModel):
    """Legacy update body - use AssignmentUpdateBody instead"""
    updated_json_content: AssignmentJsonContent = Field(..., description="Full assignment JSON matching the generation schema.")

# What the frontend sends:
class UpdateAssignmentRequest(BaseModel):
    updated_json_content: AssignmentJson

# What your service layer uses / stores:
class UpdateAssignmentInternal(UpdateAssignmentRequest):
    output_reasoning: str = Field(default="manual_edit")  # set server-side