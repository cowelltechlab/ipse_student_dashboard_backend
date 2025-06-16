from pydantic import BaseModel

class StudentClassAssociation(BaseModel):
    class_id: int
    learning_goal: str

class StudentClassOut(BaseModel):
    id: int
    name: str
    type: str
    term: str

    class Config:
        from_attributes = True  # for Pydantic v2
