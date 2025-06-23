import pyodbc
from application.database.mssql_connection import get_sql_db_connection
from application.database.mssql_crud_helpers import (
    create_record, 
    fetch_by_id, 
    update_record,
    fetch_all
)

TABLE_NAME = "Assignments"

''' 
*** GET ASSIGNMENTS ENDPOINT *** 
Fetch all assignments in Assignments table
'''
def get_all_assignments():
    """
    Fetch all assignments with student first and last names.
    """
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        query = """
        SELECT 
            a.id,
            a.student_id,
            a.title,
            a.class_id,
            a.date_created,
            a.blob_url,
            a.source_format,
            u.first_name,
            u.last_name
        FROM Assignments a
        INNER JOIN Students s ON a.student_id = s.id
        INNER JOIN Users u ON s.user_id = u.id
        """
        cursor.execute(query)
        records = cursor.fetchall()
        column_names = [column[0] for column in cursor.description]
        return [dict(zip(column_names, row)) for row in records]
    except pyodbc.Error as e:
        return {"error": str(e)}
    finally:
        conn.close()

''' 
*** GET ASSIGNMENTS BY ID ENDPOINT *** 
Fetch assignments in Assignments table based on ID
'''
def get_assignments_by_id(assignment_id):
    """
    Fetch a single assignment and include student first and last name.
    """
    conn = get_sql_db_connection()
    cursor = conn.cursor()

    try:
        query = """
        SELECT 
            a.id,
            a.student_id,
            a.title,
            a.class_id,
            a.content,
            a.date_created,
            a.blob_url,
            a.source_format,
            a.html_content,
            u.first_name,
            u.last_name
        FROM Assignments a
        INNER JOIN Students s ON a.student_id = s.id
        INNER JOIN Users u ON s.user_id = u.id
        WHERE a.id = ?
        """
        cursor.execute(query, (assignment_id,))
        record = cursor.fetchone()
        if not record:
            return None
        column_names = [column[0] for column in cursor.description]
        return dict(zip(column_names, record))
    except pyodbc.Error as e:
        return {"error": str(e)}
    finally:
        conn.close()

''' 
*** POST ASSIGNMENT ENDPOINT *** 
Add a new Assignment in Assignments table
'''
def add_assignment(data):
    return create_record(TABLE_NAME, data)

''' 
*** UPDATE ASSIGNMENT ENDPOINT *** 
Update existing assignment in Assignments table
'''
def update_assignment(assignment_id, data):
    return update_record(TABLE_NAME, assignment_id, data)