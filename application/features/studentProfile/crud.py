from azure.cosmos import CosmosClient
from application.features.studentProfile.schemas import StudentProfileCreate, StudentProfileUpdate
from application.database.nosql_connection import get_cosmos_db_connection  

DATABASE_NAME = "ai-prompt-storage"
CONTAINER_NAME = "ai-student-profile"

client = get_cosmos_db_connection()
db = client.get_database_client(DATABASE_NAME)
container = db.get_container_client(CONTAINER_NAME)

def create_profile(data: StudentProfileCreate):
    doc = data.dict()
    doc["id"] = str(doc["student_id"])
    response = container.create_item(body=doc)
    return response

def get_profile(student_id: int):
    query = "SELECT * FROM c WHERE c.student_id = @student_id"
    params = [{"name": "@student_id", "value": student_id}]
    items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    return items[0] if items else None

def update_profile(student_id: int, update_data: StudentProfileUpdate):
    existing = get_profile(student_id)
    if not existing:
        return None
    for field, value in update_data.dict(exclude_unset=True).items():
        existing[field] = value
    container.replace_item(item=existing['id'], body=existing)
    return existing

def delete_profile(student_id: int):
    profile = get_profile(student_id)
    if not profile:
        return None
    container.delete_item(item=profile['id'], partition_key=profile['student_id'])
    return {"deleted": True}
