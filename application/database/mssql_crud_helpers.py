from application.database.mssql_connection import get_sql_db_connection
import pyodbc


def fetch_all(table_name):
    """Generic function to fetch all records from a given metadata table."""
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"SELECT * FROM {table_name}")
        records = cursor.fetchall()
        column_names = [column[0] for column in cursor.description]
        return [dict(zip(column_names, row)) for row in records]
    except pyodbc.Error as e:
        return {"error": str(e)}
    finally:
        conn.close()

def fetch_all_students_with_names():
    """Fetch all students with their first and last names joined from Users table."""
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        query = """
        SELECT 
            s.id, 
            u.first_name, 
            u.last_name, 
            s.user_id,
            s.year_id, 
            s.reading_level, 
            s.writing_level
        FROM Students s
        JOIN Users u ON s.user_id = u.id
        """
        cursor.execute(query)
        records = cursor.fetchall()
        column_names = [column[0] for column in cursor.description]
        return [dict(zip(column_names, row)) for row in records]

    except pyodbc.Error as e:
        return {"error": str(e)}
    finally:
        conn.close()

def fetch_by_id(table_name, record_id):
    """Generic function to fetch a single record by ID, with special join for students."""
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
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
    finally:
        conn.close()



def create_record(table_name, data):
    """Generic function to insert a new record into a metadata table and return the created record."""
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
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
        conn.rollback()
        return {"error": str(e)}

    finally:
        conn.close()


def update_record(table_name, record_id, update_data):
    """Generic function to update an existing metadata record and return the updated record."""
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
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
        conn.rollback()
        return {"error": str(e)}

    finally:
        conn.close()


def delete_record(table_name, record_id):
    """Generic function to delete a metadata record."""
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (record_id,))
        conn.commit()

        return {"message": f"Record deleted from {table_name}"}
    except pyodbc.Error as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        conn.close()
