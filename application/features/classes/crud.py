from fastapi import HTTPException
from application.database.mssql_connection import get_sql_db_connection
from application.database.mssql_crud_helpers import (
    create_record, 
    delete_record, 
    fetch_by_id, 
    update_record,
    fetch_all
)

#TABLE_NAME = "Classes"
TABLE_NAME = "Classes"

''' 
*** GET CLASSES ENDPOINT *** 
Fetch all classes in Classes table
'''
def get_all_classes():
    return fetch_all(TABLE_NAME)

def get_classes_by_student_id(student_id):
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            query = """
            SELECT c.id, c.name, c.type, c.term, c.course_code
            FROM Classes c
            JOIN StudentClasses sc ON sc.class_id = c.id
            WHERE sc.student_id = ?
            """
            cursor.execute(query, (student_id,))
            rows = cursor.fetchall()
            if not rows:
                return []

            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

''' 
*** GET CLASSES BY ID ENDPOINT *** 
Fetch class in Classes table based on ID
'''
def get_class_by_id(class_id):
    return fetch_by_id(TABLE_NAME, class_id)

''' 
*** POST CLASS ENDPOINT *** 
Add a new Class in Classes table
'''
def add_class(data):
    return create_record(TABLE_NAME, data)

''' 
*** UPDATE CLASS ENDPOINT *** 
Update existing Class in Classes table
'''
def update_class(class_id, data):
    return update_record(TABLE_NAME, class_id, data)

''' 
*** DELETE CLASS ENDPOINT *** 
Delete a Class
'''
def delete_class(class_id):
    return delete_record(TABLE_NAME, class_id)