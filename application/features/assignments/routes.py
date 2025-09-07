import datetime
from io import BytesIO
from typing import List
from fastapi import Depends, File, Form, HTTPException, APIRouter, UploadFile, status, Body


from application.features.assignments.schemas import (
    AssignmentCreate, 
    AssignmentListResponse, 
    AssignmentDetailResponse, 
    AssignmentUpdate,
    AssignmentTypeListResponse
)
from application.features.assignments.crud import (
    get_all_assignment_types,
    get_all_assignments_by_student_id, 
    get_assignment_by_id, 
    get_all_assignments, 
    add_assignment,
    add_many_assignments, 
    update_assignment
)
from application.features.auth.permissions import require_user_access
from application.services.html_extractors import extract_html_from_file
from application.services.upload_to_blob import upload_to_blob
from application.services.text_extractors import extract_text_from_file


# router = APIRouter()
''' Prepend all classes routes with /assignments and collect all assignment-relevant endpoints under assignments tag in SwaggerUI'''
router = APIRouter()


@router.get("/", response_model=List[AssignmentListResponse])
def fetch_assignments(
    user_data = Depends(require_user_access)
):

    # If user is a Peer Tutor, filter assignments to only those of their assigned students
    caller_roles = user_data.get("role_names")

    tutor_user_id = None
    if "Peer Tutor" in caller_roles:
        tutor_user_id = user_data.get("user_id")

    
    """Retrieve all assignments"""
    assignments = get_all_assignments(tutor_user_id=tutor_user_id)

    return assignments


@router.get("/id/{assignment_id}", response_model=AssignmentDetailResponse)
def fetch_assignment_by_id(
    assignment_id: int,
    _user = Depends(require_user_access)
):
    raw_data = get_assignment_by_id(assignment_id)
    if not raw_data:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    assignment_response = {
        "assignment_id": raw_data["assignment_id"],
        "title": raw_data["assignment_title"],
        "content": raw_data["assignment_content"],
        "date_created": raw_data["assignment_date_created"],
        "blob_url": raw_data.get("assignment_blob_url"),
        "source_format": raw_data.get("assignment_source_format"),
        "html_content": raw_data.get("assignment_html_content"),
        "assignment_type": raw_data.get("assignment_type"),
        "assignment_type_id": raw_data.get("assignment_type_id"),

        # Nested Student
        "student": {
            "id": raw_data["student_internal_id"],
            "first_name": raw_data["student_first_name"],
            "last_name": raw_data["student_last_name"]
        },

        # Nested Class Info
        "class_info": {
            "id": raw_data.get("class_id"),
            "name": raw_data.get("class_name"),
            "course_code": raw_data.get("class_course_code")
        } if raw_data.get("class_id") else None,

        # NoSQL metadata
        "finalized": raw_data.get("finalized"),
        "rating_status": raw_data.get("rating_status"),
        "date_modified": raw_data.get("date_modified"),  
        "versions": raw_data.get("versions", []),
    }

    return assignment_response




@router.get(path="/types", response_model=List[AssignmentTypeListResponse])
def fetch_assignment_types(
    _user = Depends(require_user_access)
):
    """Retrieve all assignment types"""
    return get_all_assignment_types()

@router.get("/{student_id}", response_model=List[AssignmentListResponse])
def fetch_assignments(
    student_id: int,
    _user = Depends(require_user_access)
):
    """Retrieve all assignments by student ID"""
    return get_all_assignments_by_student_id(student_id)


@router.post("/", response_model=AssignmentDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    assignment_data: AssignmentCreate,
    _user = Depends(require_user_access)

                            ):
    """Create a new assignment."""
    created_assignment = add_assignment(assignment_data.model_dump())
    return created_assignment


@router.post("/upload", response_model=AssignmentDetailResponse)
async def upload_assignment_file(
    student_id: int = Form(...),
    title: str = Form(...),
    class_id: int = Form(...),
    file: UploadFile = File(...),

    _user = Depends(require_user_access)

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
async def create_many_assignments(
    assignment_data: List[AssignmentCreate],
    _user = Depends(require_user_access)
) -> List:
    
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
    assignment_type_id: int = Form(...),

    _user = Depends(require_user_access)
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
def update_class_route(
    assignment_id: int, 
    data: AssignmentUpdate = Body(...),
    _user = Depends(require_user_access)
):
    """Update a class."""
    updated_assignment = update_assignment(assignment_id, data.dict(exclude_unset=True))
    if "error" in updated_assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=updated_assignment["error"])
    return updated_assignment