from pydantic import BaseModel


class StudentBase(BaseModel):
    first_name: str
    last_name: str
    year_id: int
    reading_level: int
    writing_level: int


class StudentCreate(StudentBase):
    """Schema for creating a new student record."""
    pass

class StudentUpdate(StudentBase):
    """Schema for updating an existing student record."""
    pass

class StudentResponse(StudentBase):
    """Schema for returning a student record."""

    id: int

    class Config:
        orm_mode = True