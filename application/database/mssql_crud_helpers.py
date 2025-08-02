from application.database.mssql_connection import get_sql_db_connection
import pyodbc
from typing import List, Dict


def fetch_all(table_name: str):
    """Generic function to fetch all records from a given metadata table."""
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name}")
            records = cursor.fetchall()
            column_names = [column[0] for column in cursor.description]
            return [dict(zip(column_names, row)) for row in records]
    except pyodbc.Error as e:
        return {"error": str(e)}



def fetch_by_id(table_name, record_id):
    """Generic function to fetch a single record by ID, with special join for students."""

    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            if table_name == "Students":
                query = """
                SELECT s.id, s.user_id, s.year_id, s.reading_level, s.writing_level,
                    u.first_name, u.last_name
                FROM students s
                JOIN users u ON s.user_id = u.id
                WHERE s.id = ?
                """
                cursor.execute(query, (record_id,))
            else:
                # Generic simple query for other tables
                query = f"SELECT * FROM {table_name} WHERE id = ?"
                cursor.execute(query, (record_id,))

            record = cursor.fetchone()
            if not record:
                return None

            column_names = [column[0] for column in cursor.description]
            return dict(zip(column_names, record))

    except pyodbc.Error as e:
        return {"error": str(e)}

def create_record(table_name, data):
    """Generic function to insert a new record into a metadata table and return the created record."""

    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["?" for _ in data])
            values = tuple(data.values())

            # Use OUTPUT INSERTED.* to fetch the newly inserted row
            query = f"""
            INSERT INTO {table_name} ({columns}) 
            OUTPUT INSERTED.*
            VALUES ({placeholders})
            """

            cursor.execute(query, values)
            inserted_record = cursor.fetchone()

            # Get column names dynamically
            column_names = [column[0] for column in cursor.description]
            record_dict = dict(zip(column_names, inserted_record))

            conn.commit()
            return record_dict  # ✅ Return the inserted record instead of a message

    except pyodbc.Error as e:
        return {"error": str(e)}


def create_many_records(table_name, data_list) -> List[Dict]:
    """
    Generic function to insert multiple new records into a metadata table and 
    return the created records.
    """
    if not data_list:
        return []

    inserted_records = []

    try:
        with get_sql_db_connection() as conn:
            with conn.cursor() as cursor:
                columns = ", ".join(data_list[0].keys())
                placeholders = ", ".join(["?" for _ in data_list[0]])

                query = f"""
                INSERT INTO {table_name} ({columns}) 
                OUTPUT INSERTED.*
                VALUES ({placeholders})
                """

                for i, data in enumerate(data_list):
                    cursor.execute(query, tuple(data.values()))
                    row = cursor.fetchone()

                    if i == 0:  # Grab column names once
                        column_names = [desc[0] for desc in cursor.description]

                    inserted_records.append(dict(zip(column_names, row)))

                conn.commit()
                return inserted_records

    except pyodbc.Error as e:
        return [{"error": str(e)}]

    except Exception as e:
        return [{"error": f"An unexpected error occurred: {str(e)}"}]



def update_record(table_name, record_id, update_data):
    """Generic function to update an existing metadata record and return the updated record."""

    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            # Check if record exists
            cursor.execute(f"SELECT id FROM {table_name} WHERE id = ?", (record_id,))
            existing_record = cursor.fetchone()
            if not existing_record:
                return {"error": f"Record with id {record_id} not found in {table_name}"}

            # Build update query
            update_fields = ", ".join([f"{key} = ?" for key in update_data.keys()])
            values = list(update_data.values()) + [record_id]

            query = f"UPDATE {table_name} SET {update_fields} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()

            # Fetch the updated record
            cursor.execute(f"SELECT * FROM {table_name} WHERE id = ?", (record_id,))
            updated_record = cursor.fetchone()

            # Get column names dynamically
            column_names = [column[0] for column in cursor.description]
            record_dict = dict(zip(column_names, updated_record))

            return record_dict  # ✅ Return the updated record

    except pyodbc.Error as e:
        return {"error": str(e)}



def delete_record(table_name, record_id):
    """Generic function to delete a metadata record."""

    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (record_id,))
            rows_deleted = cursor.rowcount
            conn.commit()

            if rows_deleted == 0:
                return {"error": f"No record with id {record_id} found in {table_name}"}
            return {"message": f"Record deleted from {table_name}"}
    except pyodbc.Error as e:
        return {"error": str(e)}