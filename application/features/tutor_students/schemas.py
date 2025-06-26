from pydantic import BaseModel

class TutorStudentCreate(BaseModel):
    user_id: int       # Tutor user ID
    student_id: int

class TutorStudentResponse(BaseModel):
    id: int
    tutor_id: int
    tutor_name: str
    student_id: int
    student_name: str
