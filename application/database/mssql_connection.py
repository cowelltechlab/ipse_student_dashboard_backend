import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

def get_sql_db_connection():
    sql_url = os.getenv("SQL_URL")
    conn = pyodbc.connect(sql_url)
    return conn
