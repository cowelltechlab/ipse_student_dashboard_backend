#  SQL pulling generic student information from Students table
#  To be used, for example, in an admin's login page to view a list of all students 

from http.client import HTTPException
from typing import List
from fastapi import APIRouter, Depends, status

from application.features.auth.permissions import require_user_access
from application.features.students.crud import get_all_students, get_student_by_id, add_student, delete_student, update_student
from application.features.students.schemas import StudentResponse, StudentCreate, StudentUpdate


# router = APIRouter()
''' Prepend all student routes with /students and collect all student-relevant endpoints under Students tag in SwaggerUI'''
router = APIRouter(prefix="/students", tags=["Students"])



@router.get("/", response_model=List[StudentResponse])
def fetch_students(user_data: dict = Depends(require_user_access())):
    """Retrieve all students."""
    return get_all_students()

@router.get("/{student_id}", response_model=StudentResponse)
def fetch_student_by_id(student_id: int, user_data: dict = Depends(require_user_access())):
    """Retrieve a student by ID."""
    student = get_student_by_id(student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student with id {student_id} not found.")
    return student

@router.post("/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(student_data: StudentCreate, user_data: dict = Depends(require_user_access())):
    """Create a new student."""
    created_student = add_student(student_data.dict())
    if "error" in created_student:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=created_student["error"])
    return created_student

@router.put("/{student_id}", response_model=StudentResponse)
def update_student(student_id: int, update_data: StudentUpdate, user_data: dict = Depends(require_user_access())):
    """Update a student."""
    updated_student = update_student(student_id, update_data.dict())
    if "error" in updated_student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=updated_student["error"])
    return updated_student

@router.delete("/{student_id}")
def delete_student(student_id: int, user_data: dict = Depends(require_user_access())):
    """Delete a student."""
    result = delete_student(student_id)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return {"message": f"Student with id {student_id} deleted successfully."}