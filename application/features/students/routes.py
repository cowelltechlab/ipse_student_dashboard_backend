#  SQL pulling generic student information from Students table
#  To be used, for example, in an admin's login page to view a list of all students 

from typing import List
from fastapi import APIRouter, Depends

from application.features.auth.permissions import require_user_access
from application.features.students.crud import get_all_students
from application.features.students.schemas import StudentResponse


router = APIRouter()


@router.get("/", response_model=List[StudentResponse])
def fetch_students(user_data: dict = Depends(require_user_access())):
    """Retrieve all students."""
    return get_all_students()