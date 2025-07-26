from http.client import HTTPException
import pyodbc

from application.features.studentClasses.schema import StudentClassAssociation
from application.database.mssql_connection import get_sql_db_connection

def get_classes_for_student(student_id: int):
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
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
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


def add_student_to_class(student_id: int, association: StudentClassAssociation):
    try:
        with get_sql_db_connection() as conn:
                cursor = conn.cursor()
                # Check if student exists
                cursor.execute("SELECT 1 FROM Students WHERE id = ?", (student_id,))
                if cursor.fetchone() is None:
                    raise Exception(f"Student {student_id} not found")

                # Check if class exists in Classes table
                cursor.execute("SELECT 1 FROM Classes WHERE id = ?", (association.class_id,))
                if cursor.fetchone() is None:
                    raise Exception(f"Class {association.class_id} not found in Classes")

                # Insert association record into StudentClasses table
                insert_query = """
                    INSERT INTO StudentClasses (student_id, class_id, learning_goal)
                    VALUES (?, ?, ?)
                """
                cursor.execute(insert_query, (student_id, association.class_id, association.learning_goal))
                conn.commit()
    except HTTPException:
        raise
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")



def remove_student_from_class(student_id: int, class_id: int):
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            # Check if the association exists
            cursor.execute("""
                SELECT 1 FROM StudentClasses
                WHERE student_id = ? AND class_id = ?
            """, (student_id, class_id))
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="Student-class association not found")

            # Delete the association
            cursor.execute("""
                DELETE FROM StudentClasses
                WHERE student_id = ? AND class_id = ?
            """, (student_id, class_id))

            conn.commit()

    except HTTPException:
        raise 
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
