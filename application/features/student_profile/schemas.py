from pydantic import BaseModel, Field, conlist
from typing import Annotated, List, Dict, Optional

class StudentProfileBase(BaseModel):
    strengths: List[str]
    challenges: List[str]
    short_term_goals: str
    long_term_goals: str
    best_ways_to_help: List[str]
    summaries: Optional[Dict[str, str]] = None
    vision: Optional[str] = None


class ClassSelection(BaseModel):
    class_id: int
    class_goal: str

class StudentProfileCreate(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    year_id: int
    reading_level: int
    writing_level: int
    strengths: List[str]
    challenges: List[str]
    likes_and_hobbies: Optional[str]
    short_term_goals: str
    long_term_goals: str
    best_ways_to_help: List[str] = Field(..., min_items=1)
    classes: List[ClassSelection]

class StudentProfileUpdate(BaseModel):
    strengths: Optional[List[str]] = None
    challenges: Optional[List[str]] = None
    short_term_goals: Optional[str] = None
    long_term_goals: Optional[str] = None
    best_ways_to_help: Optional[List[str]] = None
    summaries: Optional[Dict[str, str]] = None
    vision: Optional[str] = None


class StudentClass(BaseModel):
    class_id: int
    class_name: str
    course_code: str
    learning_goal: str

class ProfileSummaries(BaseModel):
    strengths_short: str
    short_term_goals: str
    long_term_goals: str
    best_ways_to_help: str
    vision: str

class StudentProfileResponse(BaseModel):
    student_id: int
    year_name: str
    classes: List[StudentClass]
    strengths: List[str]
    challenges: List[str]
    long_term_goals: str
    short_term_goals: str
    best_ways_to_help: List[str]  
    hobbies_and_interests: str
    profile_summaries: ProfileSummaries