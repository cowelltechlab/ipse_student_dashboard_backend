from application.database.mssql_crud_helpers import (
    create_record, 
)
from application.features.studentClasses.schema import StudentClassAssociation
import pyodbc
from application.database.mssql_connection import get_sql_db_connection

def get_classes_for_student(student_id: int):
    conn = get_sql_db_connection()
    with conn.cursor() as cursor:
        query = """
        SELECT c.id, c.name, c.type, c.term
        FROM StudentClasses sc
        JOIN classes c ON sc.class_id = c.id
        WHERE sc.student_id = ?
        """
        cursor.execute(query, (student_id,))
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

def add_student_to_class(student_id: int, association: StudentClassAssociation):
    conn = get_sql_db_connection()
    with conn.cursor() as cursor:
        # Check if student exists
        cursor.execute("SELECT 1 FROM Students WHERE id = ?", (student_id,))
        if cursor.fetchone() is None:
            raise Exception(f"Student {student_id} not found")

        # Check if class exists in ClassesUpdated table
        cursor.execute("SELECT 1 FROM ClassesUpdated WHERE id = ?", (association.class_id,))
        if cursor.fetchone() is None:
            raise Exception(f"Class {association.class_id} not found in ClassesUpdated")

        # Insert association record into StudentClasses table
        insert_query = """
            INSERT INTO StudentClasses (student_id, class_id, learning_goal)
            VALUES (?, ?, ?)
        """
        cursor.execute(insert_query, (student_id, association.class_id, association.learning_goal))
        conn.commit()

def remove_student_from_class(student_id: int, class_id: int):
    conn = get_sql_db_connection()
    with conn.cursor() as cursor:
        # Check if the association exists first
        cursor.execute("""
            SELECT 1 FROM StudentClasses
            WHERE student_id = ? AND class_id = ?
        """, (student_id, class_id))
        if cursor.fetchone() is None:
            raise Exception("Association not found")

        # Delete the association
        cursor.execute("""
            DELETE FROM StudentClasses
            WHERE student_id = ? AND class_id = ?
        """, (student_id, class_id))

        conn.commit()