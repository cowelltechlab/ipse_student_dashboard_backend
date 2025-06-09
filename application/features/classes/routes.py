#  SQL pulling generic student information from Students table
#  To be used, for example, in an admin's login page to view a list of all students 

from http.client import HTTPException
from typing import List, Optional
from fastapi import HTTPException, APIRouter, Depends, status, Query, Body

from application.features.auth.permissions import require_user_access
from application.features.classes.crud import get_all_classes, add_class, delete_class, update_class as crud_update_class
from application.features.classes.schemas import ClassesResponse , ClassesCreate, ClassesUpdate 
from application.features.classes.crud import get_class_by_id


# router = APIRouter()
''' Prepend all student routes with /students and collect all student-relevant endpoints under Students tag in SwaggerUI'''
router = APIRouter()

@router.get("/", response_model=List[ClassesResponse])
def fetch_classes(
    class_id: Optional[int] = Query(None),
    user_data: dict = Depends(require_user_access())
):
    """Retrieve all classes or filter by class_id."""
    return get_all_classes()

@router.get("/{class_id}", response_model=ClassesResponse)
def fetch_class_by_id(
    class_id: int,
    user_data: dict = Depends(require_user_access())
):
    class_record = get_class_by_id(class_id)
    if not class_record:
        raise HTTPException(status_code=404, detail="Class not found")
    return class_record


@router.post("/", response_model=ClassesResponse, status_code=status.HTTP_201_CREATED)
def create_student(class_data: ClassesCreate, user_data: dict = Depends(require_user_access())):
    """Create a new student."""
    created_class = add_class(class_data.dict())
    if "error" in created_class:
        print(f"Creation error: {created_class['error']}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=created_class["error"])
    return created_class


@router.put("/{class_id}", response_model=ClassesResponse)
def update_class_route(class_id: int, data: ClassesUpdate = Body(...), user_data: dict = Depends(require_user_access())):
    """Update a class."""
    updated_class = crud_update_class(class_id, data.dict(exclude_unset=True))
    if "error" in updated_class:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=updated_class["error"])
    return updated_class


@router.delete("/{class_id}")
def delete_class(class_id: int, user_data: dict = Depends(require_user_access())):
    """Delete a class."""
    result = delete_class(class_id)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return {"message": f"Class with id {class_id} deleted successfully."}