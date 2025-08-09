from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from application.features.assignment_version_generation.schemas import LearningPathwayOption
from application.features.student_profile.schemas import StudentProfileResponse


class RatingGoals(BaseModel):
    goals_supported: List[str]
    agreement_level: Optional[str] = Field(None, description="Likert scale: strongly disagree to strongly agree")
    explanation_goals: Optional[str] = None

class RatingOptions(BaseModel):
    student_selected_options: List[str]
    assignment_sections: List[str]
    explanation_options: Optional[str] = None

class RatingFuturePlanning(BaseModel):
    learned_skills_to_apply: Optional[str] = Field(None, description="Likert scale")
    explanation_learned_skills: Optional[str] = None
    identified_changes: Optional[str] = Field(None, description="Likert scale")
    explanation_new_changes: Optional[str] = None
    confidence_level: Optional[str] = Field(None, description="Likert scale")
    explanation_confidence_level: Optional[str] = None

class RatingUpdateRequest(BaseModel):
    rating_goals: Optional[RatingGoals] = None
    rating_options: Optional[RatingOptions] = None
    rating_future_planning: Optional[RatingFuturePlanning] = None
    date_modified: Optional[datetime] = Field(default_factory=datetime.utcnow)





class AssignmentRatingData(BaseModel):
    assignment_version_id: str
    assignment_id: str
    assignment_name: str
    generated_options: List[LearningPathwayOption]
    original_assignment_html: str
    version_html: str
    student_profile: StudentProfileResponse
     rating_goals