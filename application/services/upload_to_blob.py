from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import ContentSettings
import uuid
import os

from dotenv import load_dotenv
from fastapi import UploadFile

load_dotenv()

storage_account_connection_string = os.getenv("STORAGE_ACCOUNT_CONNECTION_STRING")
container_name = "assignment-files"

async def upload_to_blob(file: UploadFile, file_bytes: bytes):
    blob_service_client = BlobServiceClient.from_connection_string(storage_account_connection_string)
    blob_name = f"{uuid.uuid4()}_{file.filename}"
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    await blob_client.upload_blob(file_bytes, overwrite=True,
        content_settings=ContentSettings(content_type=file.content_type)
    )
    return blob_client.url
