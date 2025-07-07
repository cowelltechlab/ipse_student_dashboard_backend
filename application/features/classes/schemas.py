from pydantic import BaseModel
from typing import Optional


class ClassesBase(BaseModel):
    id: int
    name: str
    type: str


class ClassesCreate(BaseModel):
    """Schema for creating a new class record."""
    ''' all fields except email and year_id are nullable'''
    name: str
    term: Optional[str]
    type: Optional[str]
    course_code: Optional[str]
    pass

class ClassesUpdate(BaseModel):
    """Schema for updating a class record."""
    name: Optional[str] = None
    type: Optional[str] = None
    term: Optional[str] = None
    course_code: Optional[str]


class ClassesResponse(ClassesBase):
    """Schema for returning a class record."""

    id: int
    name: Optional[str]
    type: Optional[str]
    term: Optional[str]
    course_code: Optional[str]


    class Config:
        orm_mode = True