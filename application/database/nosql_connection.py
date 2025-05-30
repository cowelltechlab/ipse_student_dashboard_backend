from azure.cosmos import CosmosClient
import os
from dotenv import load_dotenv

load_dotenv()

def get_cosmos_db_connection():
    endpoint = os.getenv("COSMOS_ENDPOINT")
    key = os.getenv("COSMOS_KEY")
    client = CosmosClient(endpoint, key)
    return client
