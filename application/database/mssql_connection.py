import pyodbc

from application.core.config import get_settings


def get_sql_db_connection():
    settings = get_settings()
    conn = pyodbc.connect(settings.db_url)
    return conn
