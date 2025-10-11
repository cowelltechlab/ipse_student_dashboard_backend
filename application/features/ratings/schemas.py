from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from application.features.assignment_version_generation.schemas import LearningPathwayOption
from application.features.student_profile.schemas import StudentProfileResponse


# Goals Section
class GoalsRating(BaseModel):
    helped_work_towards_goals: Optional[str] = Field(None, description="Likert scale: strongly disagree, disagree, neutral, agree, strongly agree")
    which_goals: List[str] = Field(default=[], description="Selected goals: long_term, short_term, course, different, none")
    goals_explanation: Optional[str] = Field(None, description="How did the assignment help you work toward your goals?")

# Rate My Options Section  
class OptionsRating(BaseModel):
    most_helpful_parts: List[str] = Field(default=[], description="Up to 3 most helpful parts (chosen options + assignment sections)")
    most_helpful_explanation: Optional[str] = Field(None, description="Why were these helpful? Future use?")
    least_helpful_parts: List[str] = Field(default=[], description="Up to 3 least helpful parts (chosen options + assignment sections)")
    least_helpful_explanation: Optional[str] = Field(None, description="Why weren't these helpful? How to improve?")

# My Skills Subsection
class MySkillsRating(BaseModel):
    found_way_to_keep_using: Optional[str] = Field(None, description="Likert scale: strongly disagree to strongly agree")
    way_to_keep_explanation: Optional[str] = Field(None, description="What way of working/learning? How helpful? Update profile?")
    can_describe_improvements: Optional[str] = Field(None, description="Likert scale: strongly disagree to strongly agree")
    improvements_explanation: Optional[str] = Field(None, description="What could you do better? Update profile?")

# Guiding My Learning Subsection
class GuidingLearningRating(BaseModel):
    confidence_making_changes: Optional[str] = Field(None, description="Likert scale: strongly disagree to strongly agree")
    confidence_explanation: Optional[str] = Field(None, description="What makes you confident/not confident? What would help?")

# Planning for Future Section
class PlanningForFutureRating(BaseModel):
    my_skills: Optional[MySkillsRating] = None
    guiding_my_learning: Optional[GuidingLearningRating] = None

class RatingUpdateRequest(BaseModel):
    goals_section: Optional[GoalsRating] = None
    options_section: Optional[OptionsRating] = None
    planning_section: Optional[PlanningForFutureRating] = None
    date_modified: Optional[datetime] = Field(default_factory=datetime.utcnow)


class AssignmentRatingData(BaseModel):
    assignment_version_id: str
    assignment_id: str
    assignment_name: str
    generated_options: List[LearningPathwayOption]
    original_assignment_html: str
    version_html: str
    student_profile: StudentProfileResponse


class RatingUpdateResponse(BaseModel):
    success: bool
    assignment_version_id: str
    message: str
    last_rating_update: Optional[str] = None


class ExistingRatingDataResponse(BaseModel):
    assignment_version_id: str
    goals_section: Optional[GoalsRating] = None
    options_section: Optional[OptionsRating] = None
    planning_section: Optional[PlanningForFutureRating] = None
    last_rating_update: Optional[str] = None


class RatingHistoryEntry(BaseModel):
    """Historical snapshot of rating data"""
    rating_data: dict = Field(description="Complete rating data at time of snapshot")
    timestamp: str = Field(description="ISO timestamp when this rating was saved")
    update_type: str = Field(default="rating_update", description="Type of update")


class RatingHistoryResponse(BaseModel):
    """Response containing rating history for an assignment version"""
    assignment_version_id: str
    current_rating_data: Optional[dict] = None
    rating_history: List[RatingHistoryEntry] = Field(default=[], description="Historical rating snapshots, oldest to newest")
    total_updates: int = Field(description="Total number of rating updates (including current)")
