from fastapi import APIRouter, HTTPException
from typing import List, Optional
from fastapi import HTTPException, APIRouter, Depends, status, Query

from application.features.auth.permissions import require_user_access
from application.features.students.crud import fetch_all_students_with_names, add_student, get_student_by_student_id, get_student_by_user_id, update_student as crud_update_student
from application.features.students.schemas import StudentResponse, StudentCreate, StudentUpdate 
from application.features.students.crud import  get_students_by_year,  delete_student as delete_student_records

''' Prepend all student routes with /students and collect all student-relevant endpoints under Students tag in SwaggerUI'''
router = APIRouter()

@router.get("/", response_model=List[StudentResponse])
def fetch_students(
    year_id: Optional[int] = Query(None),
    user_data: dict = Depends(require_user_access)
):
    """Retrieve all students or filter by year_id."""
    if year_id is not None:
        return get_students_by_year(year_id)
    return fetch_all_students_with_names()

@router.get("/user/{user_id}", response_model=StudentResponse)
def fetch_students_by_user_id(user_id: int, user_data: dict = Depends(require_user_access)):
    """Retrieve student by user ID."""
    student = get_student_by_user_id(user_id=user_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No student found for user with id {user_id}.")
    return student


@router.get("/{student_id}", response_model=StudentResponse)
def fetch_student_by_id(student_id: int, user_data: dict = Depends(require_user_access)):
    """Retrieve a student by ID."""
    student = get_student_by_student_id(student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student with id {student_id} not found.")
    return student


@router.post("/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(student_data: StudentCreate, user_data: dict = Depends(require_user_access)):
    """Create a new student."""
    created_student = add_student(student_data.dict())
    if "error" in created_student:
        print(f"Creation error: {created_student['error']}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=created_student["error"])
    return created_student

@router.put("/{student_id}", response_model=StudentResponse)
def update_student_route(student_id: int, update_data: StudentUpdate, user_data: dict = Depends(require_user_access)):
    """Update a student."""
    updated_student = crud_update_student(student_id, update_data.dict(exclude_unset=True))
    if "error" in updated_student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=updated_student["error"])
    return updated_student


@router.delete("/{student_id}")
def delete_student(student_id: int, user_data: dict = Depends(require_user_access)):
    """Delete a student."""
    result = delete_student_records(student_id)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return {"message": f"Student with id {student_id} deleted successfully."}