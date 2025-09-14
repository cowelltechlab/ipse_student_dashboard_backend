from typing import List, Optional
from pydantic import BaseModel, EmailStr
from application.features.tutor_students.schemas import TutoredStudent



class TutoredStudent(BaseModel):
    student_id: int
    name: str

class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class StudentProfile(BaseModel):
    year_name: Optional[str] = None
    student_id: Optional[int] = None

class UserResponse(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    school_email: Optional[str] = None
    email: Optional[str] = None
    roles: Optional[List[str]] = None
    role_ids: Optional[List[int]] = None
    profile_picture_url: Optional[str] = None
    is_active: Optional[bool] = None

    profile_tag: Optional[str] = None
    
    student_profile: Optional[StudentProfile] = None
    
    invite_url: Optional[str] = None
    tutored_students: Optional[List[TutoredStudent]] = None


class RegisterUserRequest(BaseModel):
    first_name: str
    last_name: str
    password: str
    role_ids: List[int]
    school_email: str
    google_email: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    email: str
    new_password: str


class AdminResetPasswordRequest(BaseModel):
    student_id: int
    new_password: str
