import pyodbc
import os
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()

@contextmanager
def get_sql_db_connection():
    """Context manager that opens and closes the SQL connection safely."""
    sql_url = os.getenv("SQL_URL")
    conn = pyodbc.connect(sql_url, timeout=30)
    try:
        yield conn
    finally:
        conn.close()
