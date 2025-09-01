from typing import List
from pydantic import BaseModel

class TutorStudentCreate(BaseModel):
    user_id: int       # Tutor user ID
    student_id: int

class TutorStudentSyncRequest(BaseModel):
    tutor_id: int
    student_ids: List[int]

class TutorStudentResponse(BaseModel):
    id: int
    tutor_id: int
    tutor_name: str
    tutor_email: str
    student_id: int
    student_name: str
    student_email: str
    student_year_id: int
    student_year: str

    class Config:
        from_attributes = True
