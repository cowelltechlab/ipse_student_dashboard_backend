from pydantic import BaseModel
from typing import Optional


class StudentBase(BaseModel):
    first_name: str
    last_name: str
    reading_level: int
    writing_level: int


class StudentCreate(StudentBase):
    """Schema for creating a new student record."""
    ''' all fields except email and year_id are nullable'''
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    gt_email: Optional[str]
    year_id: int
    password_hash: Optional[str]
    reading_level: Optional[int]
    writing_level: Optional[int]
    profile_picture_url: Optional[str]
    pass

class StudentUpdate(BaseModel):
    """Schema for updating a student record."""
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gt_email: Optional[str] = None
    password_hash: Optional[str] = None
    year_id: Optional[int] = None
    reading_level: Optional[int] = None
    writing_level: Optional[int] = None
    profile_picture_url: Optional[str] = None
    active_status: Optional[bool] = True

class StudentResponse(StudentBase):
    id: int
    first_name: str
    last_name: str
    reading_level: int
    writing_level: int
    active_status: Optional[bool] = None
    year_name: str
    profile_picture_url: Optional[str] = None  

    class Config:
        orm_mode = True

class StudentProfilePictureResponse(BaseModel):
    student_id: int
    profile_picture_url: Optional[str]
