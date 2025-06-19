from pydantic import BaseModel
from typing import Dict, List, Optional

class Rating(BaseModel):
    difficulty: str
    best_changes: List[int]
    disliked_changes: List[int]

class AssignmentVersionBase(BaseModel):
    version_number: int
    modifier_id: int
    date_modified: str  # ISO datetime string
    content: str
    udl_reasons: Dict[str, str]
    rating: Rating
    finalized: bool
    starred: bool

class AssignmentVersionCreate(AssignmentVersionBase):
    pass

class AssignmentVersionUpdate(BaseModel):
    content: Optional[str] = None
    udl_reasons: Optional[Dict[str, str]] = None
    rating: Optional[Rating] = None
    finalized: Optional[bool] = None
    starred: Optional[bool] = None

class AssignmentVersionResponse(AssignmentVersionBase):
    # This represents a single version, without top-level document fields like 'id' or 'student_id'
    pass

# Optional: if you want to return the whole document with versions:
class AssignmentDocumentResponse(BaseModel):
    id: str
    student_id: int
    assignment_id: str
    versions: List[AssignmentVersionResponse]
