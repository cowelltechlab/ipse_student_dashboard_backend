from fastapi import APIRouter, UploadFile, File, HTTPException
from azure.storage.blob import BlobServiceClient
from application.features.students.crud import update_student_profile_pic 

router = APIRouter()
import os
from dotenv import load_dotenv

load_dotenv()
# You need your Azure Blob connection string or client somewhere
BLOB_CONNECTION_STRING = os.getenv("STORAGE_ACCOUNT_CONNECTION_STRING")
BLOB_CONTAINER_NAME = "profile-pictures"

blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)

@router.post("/students/{student_id}/profile-pic")
async def upload_profile_pic(
    student_id: int,
    file: UploadFile = File(...)
):
    # Validate file type if needed
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    try:
        # Read file content bytes
        file_content = await file.read()

        # Generate a unique blob name, e.g. "student-{student_id}-profile-pic.jpg"
        blob_name = f"student-{student_id}-profile-pic{file.filename[file.filename.rfind('.'):]}"
        
        # Upload blob
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(file_content, overwrite=True)

        # Get blob URL - assuming public container or SAS URL if private
        blob_url = blob_client.url  # this is the URL to the uploaded image

        # Update student record in SQL with the new profile_pic URL
        updated_student = update_student_profile_pic(student_id, blob_url)

        return {"profile_pic_url": blob_url, "student": updated_student}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
