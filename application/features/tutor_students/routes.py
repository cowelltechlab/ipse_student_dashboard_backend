from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from application.features.auth.permissions import require_user_access
from application.features.tutor_students.crud import add_tutor_student, delete_tutor_student_by_id, get_all_tutor_students, get_students_by_tutor, sync_tutor_students_relationships
from application.features.tutor_students.helpers import group_tutor_students
from .schemas import TutorStudentCreate, TutorStudentResponse, TutorStudentSyncRequest
from application.database.mssql_connection import get_sql_db_connection

router = APIRouter()

@router.get("/", response_model=List[TutorStudentResponse])
def get_all(user_data: dict = Depends(require_user_access)):
    return get_all_tutor_students()
    

@router.get("/grouped")
def get_grouped(user_data: dict = Depends(require_user_access)):
    flat_records = get_all_tutor_students()
    return group_tutor_students(flat_records)

@router.get("/{tutor_id}", response_model=List[TutorStudentResponse])
def get_by_tutor(tutor_id: int, user_data: dict = Depends(require_user_access)):
    return get_students_by_tutor(tutor_id)

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_relationship(data: TutorStudentCreate, user_data: dict = Depends(require_user_access)):
    result = add_tutor_student(data.user_id, data.student_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/sync", status_code=status.HTTP_200_OK)
def sync_tutor_students(
    data: TutorStudentSyncRequest,
    user_data: dict = Depends(require_user_access)
):
    return sync_tutor_students_relationships(data.tutor_id, data.student_ids)


@router.delete("/{relationship_id}")
def delete_relationship(relationship_id: int, user_data: dict = Depends(require_user_access)):
    result = delete_tutor_student_by_id(relationship_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
