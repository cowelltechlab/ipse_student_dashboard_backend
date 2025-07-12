from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import ContentSettings
import uuid
import os

from dotenv import load_dotenv
from fastapi import HTTPException, UploadFile, status

load_dotenv()

storage_account_connection_string = os.getenv("STORAGE_ACCOUNT_CONNECTION_STRING")
container_name = "assignment-files"

async def upload_to_blob_old(file: UploadFile, file_bytes: bytes):
    blob_service_client = BlobServiceClient.from_connection_string(storage_account_connection_string)
    blob_name = f"{uuid.uuid4()}_{file.filename}"
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    await blob_client.upload_blob(file_bytes, overwrite=True,
        content_settings=ContentSettings(content_type=file.content_type)
    )
    return blob_client.url


async def upload_to_blob(file: UploadFile, file_bytes: bytes):
    try:
        async with BlobServiceClient.from_connection_string(storage_account_connection_string) as blob_service_client:
            blob_name = f"{uuid.uuid4()}_{file.filename}"
            async with blob_service_client.get_blob_client(container=container_name, blob=blob_name) as blob_client:
                await blob_client.upload_blob(file_bytes, overwrite=True,
                    content_settings=ContentSettings(content_type=file.content_type)
                )
                return blob_client.url
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to Azure Blob Storage: {str(e)}"
        )