from pydantic import BaseModel, Field, HttpUrl, conlist, field_validator, validator
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
    """
    All fields optional so user can patch any subset.
    """
    strengths: Optional[List[str]] = None
    challenges: Optional[List[str]] = None
    long_term_goals: Optional[str] = None
    short_term_goals: Optional[str] = None
    hobbies_and_interests: Optional[str] = None
    best_ways_to_help: Optional[List[str]] = None
    classes: Optional[List[ClassSelection]] = None


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

class StudentProfileUpdate(BaseModel):
    year_id: Optional[int] = None
    strengths: Optional[List[str]] = None
    challenges: Optional[List[str]] = None
    likes_and_hobbies: Optional[str] = None
    short_term_goals: Optional[str] = None
    long_term_goals: Optional[str] = None
    best_ways_to_help: Optional[List[str]] = None
    classes: Optional[List[ClassSelection]] = None


class StudentProfileResponse(BaseModel):
    student_id: int
    user_id: int
   
    first_name: str
    last_name: str
    email: Optional[str]
    gt_email: Optional[str]
    year_name: str
    profile_picture_url: Optional[str]
    ppt_embed_url: Optional[str]
    ppt_edit_url: Optional[str]
    group_type: Optional[str]
    classes: List[StudentClass]
    strengths: List[str]
    challenges: List[str]
    long_term_goals: str
    short_term_goals: str
    best_ways_to_help: List[str]
    hobbies_and_interests: str
    profile_summaries: ProfileSummaries


class ClassSelection(BaseModel):
    class_id: int
    class_goal: Optional[str]


class StudentProfilePrefillResponse(BaseModel):
    user_id: int
    student_id: Optional[int]
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    gt_email: Optional[str]
    profile_picture_url: Optional[str]
    year_id: Optional[int]

    classes: Optional[List[ClassSelection]]
    strengths: List[str]
    challenges: List[str]
    long_term_goals: str
    short_term_goals: str
    best_ways_to_help: List[str]
    hobbies_and_interests: str
    reading_level: List[str]
    writing_level: List[str]


class PPtUrlsPayload(BaseModel):
    embed_url: str
    edit_url: str

    @field_validator("embed_url")
    def must_be_valid_embed_url(cls, v):
        if not v.startswith("https://gtvault-my.sharepoint.com") or "action=embedview" not in v:
            raise ValueError("embed_url must be a valid SharePoint embed link with 'action=embedview'")
        return v

    @field_validator("edit_url")
    def must_be_valid_edit_url(cls, v):
        if not v.startswith("https://gtvault-my.sharepoint.com"):
            raise ValueError("edit_url must be a valid SharePoint link")
        return v