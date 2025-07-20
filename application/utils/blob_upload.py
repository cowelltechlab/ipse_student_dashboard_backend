from azure.storage.blob import BlobServiceClient
import os
from dotenv import load_dotenv
from uuid import uuid4

load_dotenv()

BLOB_CONNECTION_STRING = os.getenv("STORAGE_ACCOUNT_CONNECTION_STRING")
BLOB_CONTAINER_NAME = "profile-pictures"

blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)


async def upload_profile_picture(user_id: int, file) -> str:
    if not file.content_type.startswith("image/"):
        raise ValueError("Invalid file type")

    contents = await file.read()
    extension = file.filename.split(".")[-1]
    blob_name = f"user-{user_id}-{uuid4().hex}.{extension}"

    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(contents, overwrite=True)

    return blob_client.url 
