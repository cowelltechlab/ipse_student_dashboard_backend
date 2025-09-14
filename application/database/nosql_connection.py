from azure.cosmos import CosmosClient
import os
from dotenv import load_dotenv

load_dotenv()

def get_cosmos_db_connection():
    endpoint = os.getenv("COSMOS_ENDPOINT")
    key = os.getenv("COSMOS_KEY")
    client = CosmosClient(endpoint, key)
    return client

def get_container():
    client = get_cosmos_db_connection()
    DATABASE_NAME = os.getenv("COSMOS_DATABASE_NAME")
    container = client.get_database_client(DATABASE_NAME).get_container_client("ai-assignment-versions-v2")
    return container