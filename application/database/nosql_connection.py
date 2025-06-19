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
    database = client.get_database_client("ai-prompt-storage")
    container = database.get_container_client("ai-prompt-version-history")
    return container