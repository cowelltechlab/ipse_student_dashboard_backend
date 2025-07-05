from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Rating(BaseModel):
    difficulty: str
    best_changes: List[int]
    disliked_changes: List[int]

class UDLReasons(BaseModel):
    Engagement: Optional[str] = None
    Expression: Optional[str] = None
    Representation: Optional[str] = None

class AssignmentVersionBase(BaseModel):
    assignment_id: str
    version_number: int
    modifier_id: int  
    date_modified: datetime
    content: Optional[str] = None
    udl_reasons: Optional[UDLReasons] = None
    rating: Optional[Rating] = None
    finalized: Optional[bool] = False
    starred: Optional[bool] = False

class AssignmentVersionCreate(AssignmentVersionBase):
    pass

class AssignmentVersionResponse(AssignmentVersionBase):
    id: str

class AssignmentVersionUpdate(BaseModel):
    content: Optional[str] = None
    udl_reasons: Optional[UDLReasons] = None
    rating: Optional[Rating] = None
    finalized: Optional[bool] = None
    starred: Optional[bool] = None
    date_modified: Optional[datetime] = None