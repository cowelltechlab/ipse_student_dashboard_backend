import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

conn_str = os.getenv("SQL_URL")
try:
    conn = pyodbc.connect(conn_str, timeout=5)
    print("Connected successfully")
except Exception as e:
    print("Connection failed:", e)