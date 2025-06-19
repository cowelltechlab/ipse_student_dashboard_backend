from fastapi import APIRouter, HTTPException, status, Body
from application.features.studentProfile.crud import (
    create_profile, get_profile, update_profile, delete_profile
)
from application.features.studentProfile.schemas import (
    StudentProfileCreate, StudentProfileResponse, StudentProfileUpdate
)

router = APIRouter()

@router.post("/", response_model=StudentProfileResponse, status_code=status.HTTP_201_CREATED)
def create_student_profile(profile: StudentProfileCreate):
    return create_profile(profile)

@router.get("/{student_id}", response_model=StudentProfileResponse)
def get_student_profile(student_id: int):
    profile = get_profile(student_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.put("/{student_id}", response_model=StudentProfileResponse)
def update_student_profile(student_id: int, update_data: StudentProfileUpdate = Body(...)):
    existing_profile = get_profile(student_id)
    if not existing_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    updated = update_profile(student_id, update_data)
    if not updated:
        raise HTTPException(status_code=400, detail="Update failed")
    return updated

@router.delete("/{student_id}")
def delete_student_profile(student_id: int):
    result = delete_profile(student_id)
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"message": "Profile deleted successfully"}
