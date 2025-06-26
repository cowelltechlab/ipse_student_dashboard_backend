from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import uuid

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
    content: str
    udl_reasons: UDLReasons
    rating: Rating
    finalized: bool
    starred: bool

class AssignmentVersionCreate(AssignmentVersionBase):
    pass

class AssignmentVersionResponse(AssignmentVersionBase):
    id: str
