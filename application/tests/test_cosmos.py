from azure.cosmos import CosmosClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get endpoint and key
endpoint = os.getenv("COSMOS_ENDPOINT")
key = os.getenv("COSMOS_KEY")

# Create Cosmos client
client = CosmosClient(endpoint, key)

# List all databases
try:
    databases = list(client.list_databases())
    print("Connection successful! Databases found:")
    for db in databases:
        print(f" - {db['id']}")
except Exception as e:
    print("Connection failed!")
    print(e)
