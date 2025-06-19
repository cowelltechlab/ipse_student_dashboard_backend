import datetime
from http.client import HTTPException
from typing import List, Optional
from fastapi import File, Form, HTTPException, APIRouter, Depends, UploadFile, status, Query, Body

from application.features.assignments.schemas import AssignmentCreate , AssignmentResponse, AssignmentUpdate 
from application.features.assignments.crud import get_assignments_by_id, get_all_assignments, add_assignment, update_assignment
from application.services.html_extractors import extract_html_from_file
from application.services.upload_to_blob import upload_to_blob
from application.services.text_extractors import extract_text_from_file


# router = APIRouter()
''' Prepend all classes routes with /assignments and collect all assignment-relevant endpoints under assignments tag in SwaggerUI'''
router = APIRouter()

@router.get("/", response_model=List[AssignmentResponse])
def fetch_assignments():
    """Retrieve all assignments"""
    return get_all_assignments()

@router.get("/{assignment_id}", response_model=AssignmentResponse)
def fetch_assignment_by_id(
    assignment_id: int,
):
    assignment_record = get_assignments_by_id(assignment_id)
    if not assignment_record:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment_record

@router.post("/", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(assignment_data: AssignmentCreate):
    """Create a new assignment."""
    created_assignment = add_assignment(assignment_data.dict())
    if "error" in created_assignment:
        print(f"Creation error: {created_assignment['error']}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=created_assignment["error"])
    return created_assignment

@router.post("/upload", response_model=AssignmentResponse)
async def upload_assignment_file(
    student_id: int = Form(...),
    title: str = Form(...),
    class_id: int = Form(...),
    file: UploadFile = File(...)
):
    # 1. Read file content once
    file_bytes = await file.read()

    # 2. Upload to Azure
    blob_url = await upload_to_blob(file, file_bytes)

    # 3. Extract raw text and HTML
    content = await extract_text_from_file(file.filename, file_bytes)
    html_content = await extract_html_from_file(file.filename, file_bytes)

    # 4. Store in database
    assignment_data = AssignmentCreate(
        student_id=student_id,
        title=title,
        class_id=class_id,
        content=content,
        html_content=html_content,
        blob_url=blob_url,
        source_format=file.filename.split(".")[-1].lower(),
        date_created=datetime.datetime.now(datetime.timezone.utc)
    )
    return create_assignment(assignment_data)


@router.put("/{assignment_id}", response_model=AssignmentResponse)
def update_class_route(assignment_id: int, data: AssignmentUpdate = Body(...)):
    """Update a class."""
    updated_assignment = update_assignment(assignment_id, data.dict(exclude_unset=True))
    if "error" in updated_assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=updated_assignment["error"])
    return updated_assignment