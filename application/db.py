import pyodbc
from contextlib import contextmanager
import logging


@contextmanager
def get_db():
    try:
        # TODO: Replace with a conncetion string composed of azure vault secrets.
        conn = pyodbc.connect(DATABASE_URL)
        try:
            yield conn
        finally:
            conn.close()
    except Exception as e:
        logging.error(f"Database connection error: {e}")
        raise
