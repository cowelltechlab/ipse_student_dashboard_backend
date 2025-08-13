from pydantic import BaseModel, Field, root_validator, validator
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


class AssignmentGenerationOptionsResponse(BaseModel):
    skills_for_success: str
    learning_pathways: List[LearningPathwayOption]
    version_document_id: str


class AssignmentVersionGenerationResponse(BaseModel):
    version_document_id: str
    json_content: Dict[str, Any]


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

    # Lightweight HTML-fragment checks (the full template-rule check still happens server-side)
    @validator("assignmentInstructionsHtml", "stepByStepPlanHtml", "promptsHtml", "motivationalMessageHtml")
    def _html_fragments(cls, v):
        if not cls._is_fragment(v):
            raise ValueError("Must be an HTML fragment without outer wrappers")
        return v

    @root_validator
    def _support_tools_fragments(cls, values):
        st = values.get("supportTools")
        if st:
            for k in ("toolsHtml", "aiPromptingHtml", "aiPolicyHtml"):
                if not cls._is_fragment(getattr(st, k)):
                    raise ValueError(f"supportTools.{k} must be an HTML fragment without outer wrappers")
        return values

class AssignmentUpdateBody(BaseModel):
    updated_json_content: AssignmentJsonContent = Field(..., description="Full assignment JSON matching the generation schema.")
    output_reasoning: Optional[str] = Field(default=None, description="Optional human note on why the update was made.")