from pydantic import BaseModel
from typing import List

class LearningPathwayOption(BaseModel):
    title: str
    description: str
    reasons: List[str]

class AssignmentGenerationOptionsResponse(BaseModel):
    skills_for_success: str
    learning_pathways: List[LearningPathwayOption]
    version_document_id: str
