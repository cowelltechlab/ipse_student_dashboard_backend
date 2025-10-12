"""
Assignment creation routes - POST operations for creating/uploading assignments
"""
import datetime
from io import BytesIO
from typing import List
from fastapi import Depends, File, Form, APIRouter, UploadFile, status

from application.features.assignments.schemas import (
    AssignmentCreate,
    AssignmentCreateResponse,
    AssignmentDetailResponse,
    AssignmentTextCreate,
    AssignmentTextBulkCreate,
)
from application.features.assignments.crud import (
    add_assignment,
    add_many_assignments,
)
from application.features.auth.permissions import require_user_access
from application.services.html_extractors import extract_html_from_file
from application.services.upload_to_blob import upload_to_blob, upload_html_as_word_to_blob
from application.services.text_extractors import extract_text_from_file
from application.features.gpt.crud import generate_html_from_text

router = APIRouter()


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
    """Upload an assignment file for a single student"""
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
    """Create multiple assignments at once."""
    assignment_data_dicts = [data.model_dump() for data in assignment_data]
    created_assignment_records = await add_many_assignments(assignment_data_dicts)
    return created_assignment_records


@router.post("/upload/bulk", response_model=List[AssignmentCreateResponse])
async def upload_many_assignment_files(
    student_ids: List[int] = Form(...),
    title: str = Form(...),
    class_id: int = Form(...),
    file: UploadFile = File(...),
    assignment_type_id: int = Form(...),
    _user = Depends(require_user_access)
):
    """Upload the same assignment file for multiple students"""
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
    response = await create_many_assignments(assignment_data)
    return response


@router.post("/text", response_model=AssignmentDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment_from_text(
    assignment_data: AssignmentTextCreate,
    _user = Depends(require_user_access)
):
    """Create a new assignment from raw text content."""
    # Generate HTML content from text using GPT
    html_content = generate_html_from_text(assignment_data.content)

    # Upload HTML content as Word document to blob storage
    blob_url = await upload_html_as_word_to_blob(
        html_content=html_content,
        title=assignment_data.title,
        student_id=assignment_data.student_id
    )

    # Convert to AssignmentCreate schema
    assignment_create_data = AssignmentCreate(
        student_id=assignment_data.student_id,
        title=assignment_data.title,
        class_id=assignment_data.class_id,
        content=assignment_data.content,
        html_content=html_content,  # GPT-generated HTML content
        blob_url=blob_url,  # Word document download URL
        source_format="docx",  # Mark as Word document
        date_created=assignment_data.date_created or datetime.datetime.now(datetime.timezone.utc),
        assignment_type_id=assignment_data.assignment_type_id
    )

    created_assignment = add_assignment(assignment_create_data.model_dump())
    return created_assignment


@router.post("/text/bulk", response_model=List[AssignmentCreateResponse], status_code=status.HTTP_201_CREATED)
async def create_many_assignments_from_text(
    assignment_data: AssignmentTextBulkCreate,
    _user = Depends(require_user_access)
):
    """Create assignments for multiple students using the same raw text content."""
    # Generate HTML content once for all students (efficiency)
    html_content = generate_html_from_text(assignment_data.content)

    assignment_create_list = []

    for student_id in assignment_data.student_ids:
        # Create unique Word document for each student
        blob_url = await upload_html_as_word_to_blob(
            html_content=html_content,
            title=assignment_data.title,
            student_id=student_id
        )

        assignment_create_list.append(
            AssignmentCreate(
                student_id=student_id,
                title=assignment_data.title,
                class_id=assignment_data.class_id,
                content=assignment_data.content,
                html_content=html_content,  # GPT-generated HTML content (reused)
                blob_url=blob_url,  # Unique Word document download URL per student
                source_format="docx",  # Mark as Word document
                date_created=datetime.datetime.now(datetime.timezone.utc),
                assignment_type_id=assignment_data.assignment_type_id
            )
        )

    # Use existing bulk creation logic
    assignment_data_dicts = [data.model_dump() for data in assignment_create_list]
    created_assignment_records = await add_many_assignments(assignment_data_dicts)
    return created_assignment_records
