from pydantic import BaseModel
from typing import Any, Dict, List

class LearningPathwayOption(BaseModel):
    name: str
    description: str
    why_good_existing: str
    why_good_growth: str
    internal_id: str


class AssignmentGenerationOptionsResponse(BaseModel):
    skills_for_success: str
    learning_pathways: List[LearningPathwayOption]
    version_document_id: str


class AssignmentVersionGenerationResponse(BaseModel):
    version_document_id: str
    json_content: Dict[str, Any]

class AssignmentUpdateBody(BaseModel):
    updated_json_content: dict