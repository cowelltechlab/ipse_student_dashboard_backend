from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AssignmentBase(BaseModel):
    id: Optional[int] = None
    student_id: int
    title: str
    class_id: int
    content: str
    date_created: datetime


class AssignmentCreate(BaseModel):
    """Schema for creating a new assignment record."""
    ''' all fields except email and year_id are nullable'''
    student_id: Optional[int] = None
    title: Optional[str] = None
    class_id: Optional[int] = None
    content: Optional[str] = None
    date_created: Optional[datetime] = None
    pass

class AssignmentUpdate(BaseModel):
    """Schema for updating an assignment record."""
    student_id: Optional[int] = None
    title: Optional[str] = None
    class_id: Optional[int] = None
    content: Optional[str] = None
    date_created: Optional[datetime] = None
    pass

class AssignmentResponse(AssignmentBase):
    """Schema for returning an assignment record."""
    id: int
    student_id: Optional[int] = None
    title: Optional[str] = None
    class_id: Optional[int] = None
    content: Optional[str] = None
    date_created: Optional[datetime] = None


    class Config:
        orm_mode = True