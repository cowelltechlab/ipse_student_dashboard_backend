from azure.cosmos import CosmosClient, PartitionKey
import os

from dotenv import load_dotenv

load_dotenv()

def get_cosmos_db_connection():
    endpoint = os.getenv("COSMOS_ENDPOINT")
    key = os.getenv("COSMOS_KEY")
    client = CosmosClient(endpoint, key)
    return client


DB_NAME = "ai-prompt-storage"
OLD_CONTAINER = "ai-assignment-versions"
NEW_CONTAINER = "ai-assignment-versions-v2"

client = get_cosmos_db_connection()
database = client.get_database_client(DB_NAME)
old_container = database.get_container_client(OLD_CONTAINER)
new_container = database.get_container_client(NEW_CONTAINER)

# Read all documents and migrate
for doc in old_container.read_all_items():
    # Ensure the id is a string (Cosmos requires this)
    doc["id"] = str(doc["id"])
    
    # Insert into the new container
    new_container.create_item(body=doc)

print("Migration complete!")
