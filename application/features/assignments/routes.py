import datetime
from http.client import HTTPException
from io import BytesIO
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
    add_assignment,
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


@router.get("/id/{assignment_id}", response_model= AssignmentDetailResponse)
def fetch_assignment_by_id(
    assignment_id: int,
):
    assignment_record = get_assignments_by_id(assignment_id)
    if not assignment_record:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment_record


@router.get(path="/types", response_model=List[AssignmentTypeListResponse])
def fetch_assignment_types():
    """Retrieve all assignment types"""
    print("REQUEST RECEIVED")
    return get_all_assignment_types()


@router.post("/", response_model=AssignmentDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(assignment_data: AssignmentCreate):
    """Create a new assignment."""
    created_assignment = add_assignment(assignment_data.model_dump())
    return created_assignment


@router.post("/upload", response_model=AssignmentDetailResponse)
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
    return await create_assignment(assignment_data)


@router.post("/bulk", response_model=List[AssignmentDetailResponse], status_code=status.HTTP_201_CREATED)
async def create_many_assignments(assignment_data: List[AssignmentCreate]) -> List:
    """Create a new assignment."""
    assignment_data_dicts = [data.model_dump() for data in assignment_data]
    created_assignment_records = await add_many_assignments(assignment_data_dicts)
    return created_assignment_records


@router.post("/upload/bulk", response_model=List[AssignmentDetailResponse])
async def upload_many_assignment_files(
    student_ids: List[int] = Form(...),
    title: str = Form(...),
    class_id: int = Form(...),
    file: UploadFile = File(...),
    assignment_type_id: int = Form(...)
):
    # 1. Read file content once. UploadFile can only be read once.
    original_file_bytes = await file.read()
    original_filename = file.filename

    assignment_data = []
    for student_id in student_ids:
        in_memory_file = BytesIO(original_file_bytes)

        file_copy = UploadFile(
            filename=original_filename,
            file=in_memory_file
        )

         # 2. Upload to Azure
        blob_url = await upload_to_blob(file_copy, original_file_bytes)

        # 3. Extract raw text and HTML
        content = await extract_text_from_file(original_filename, original_file_bytes)
        html_content = await extract_html_from_file(original_filename, original_file_bytes)

        # 4. Create unique assignment for each student
        assignment_data.append(
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
            )
        )
    
    # 5. Store in SQL DB
    return await create_many_assignments(assignment_data)


@router.put("/id/{assignment_id}", response_model=AssignmentDetailResponse)
def update_class_route(assignment_id: int, data: AssignmentUpdate = Body(...)):
    """Update a class."""
    updated_assignment = update_assignment(assignment_id, data.dict(exclude_unset=True))
    if "error" in updated_assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=updated_assignment["error"])
    return updated_assignment