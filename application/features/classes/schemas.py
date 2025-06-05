from pydantic import BaseModel
from typing import Optional


class ClassesBase(BaseModel):
    id: int
    name: str
    type: str


class ClassesCreate(BaseModel):
    """Schema for creating a new student record."""
    ''' all fields except email and year_id are nullable'''
    name: str
    type: Optional[str]
    pass

class ClassesUpdate(BaseModel):
    """Schema for updating a student record."""
    name: Optional[str] = None
    type: Optional[str] = None

class ClassesResponse(ClassesBase):
    """Schema for returning a student record."""

    id: int
    name: Optional[str]
    type: Optional[str]

    class Config:
        orm_mode = True