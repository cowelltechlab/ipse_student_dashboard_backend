import datetime
from http.client import HTTPException
from typing import List
from fastapi import File, Form, HTTPException, APIRouter, UploadFile, status, Body


from application.features.assignments.schemas import (
    AssignmentCreate, 
    AssignmentListResponse, 
    AssignmentDetailResponse, 
    AssignmentUpdate,
    AssignmentTypeListResponse
)
from application.features.assignments.crud import (
    get_all_assignment_types, 
    get_assignments_by_id, 
    get_all_assignments, 
    add_many_assignments, 
    update_assignment
)
from application.services.html_extractors import extract_html_from_file
from application.services.upload_to_blob import upload_to_blob
from application.services.text_extractors import extract_text_from_file


# router = APIRouter()
''' Prepend all classes routes with /assignments and collect all assignment-relevant endpoints under assignments tag in SwaggerUI'''
router = APIRouter()

@router.get("/", response_model=List[AssignmentListResponse])
def fetch_assignments():
    """Retrieve all assignments"""
    return get_all_assignments()

@router.post("/upload", response_model=List[AssignmentDetailResponse])
async def upload_assignment_file(
    student_ids: List[int] = Form(...),
    title: str = Form(...),
    class_id: int = Form(...),
    file: UploadFile = File(...),
    assignment_type_id: int = Form(...)
):
    # 1. Read file content once
    file_bytes = await file.read()

    # 2. Upload to Azure
    blob_url = await upload_to_blob(file, file_bytes)

    # 3. Extract raw text and HTML
    content = await extract_text_from_file(file.filename, file_bytes)
    html_content = await extract_html_from_file(file.filename, file_bytes)

    # 4. Store in database
    assignment_data = [
        AssignmentCreate(
            student_id=student_id,
            title=title,
            class_id=class_id,
            content=content,
            html_content=html_content,
            blob_url=blob_url,
            source_format=file.filename.split(".")[-1].lower(),
            date_created=datetime.datetime.now(datetime.timezone.utc),
            assignment_type_id=assignment_type_id
        ) for student_id in student_ids
    ]
    return await create_assignment(assignment_data)


@router.get(path="/types", response_model=List[AssignmentTypeListResponse])
def fetch_assignment_types():
    """Retrieve all assignment types"""
    return get_all_assignment_types()


@router.get("/{assignment_id}", response_model= AssignmentDetailResponse)
def fetch_assignment_by_id(
    assignment_id: int,
):
    assignment_record = get_assignments_by_id(assignment_id)
    if not assignment_record:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment_record

@router.post("/", response_model=List[AssignmentDetailResponse], status_code=status.HTTP_201_CREATED)
async def create_assignment(assignment_data: List[AssignmentCreate]) -> List:
    """Create a new assignment."""
    assignment_data_dicts = [data.model_dump() for data in assignment_data]
    created_assignment_records = await add_many_assignments(assignment_data_dicts)
    return created_assignment_records


@router.put("/{assignment_id}", response_model=AssignmentDetailResponse)
def update_class_route(assignment_id: int, data: AssignmentUpdate = Body(...)):
    """Update a class."""
    updated_assignment = update_assignment(assignment_id, data.dict(exclude_unset=True))
    if "error" in updated_assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=updated_assignment["error"])
    return updated_assignment
