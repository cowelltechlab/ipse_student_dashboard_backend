from pydantic import BaseModel
from typing import List, Dict, Optional

class StudentProfileBase(BaseModel):
    strengths: List[str]
    challenges: List[str]
    short_term_goals: str
    long_term_goals: str
    best_ways_to_help: List[str]
    summaries: Optional[Dict[str, str]] = None
    vision: Optional[str] = None

class StudentProfileCreate(StudentProfileBase):
    student_id: int

class StudentProfileUpdate(BaseModel):
    strengths: Optional[List[str]] = None
    challenges: Optional[List[str]] = None
    short_term_goals: Optional[str] = None
    long_term_goals: Optional[str] = None
    best_ways_to_help: Optional[List[str]] = None
    summaries: Optional[Dict[str, str]] = None
    ision: Optional[str] = None

class StudentProfileResponse(StudentProfileCreate):
    id: str  # Cosmos document ID
