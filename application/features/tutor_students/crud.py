from fastapi import HTTPException
import pyodbc

from typing import List
from application.database.mssql_connection import get_sql_db_connection


def get_all_tutor_students():
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    ts.id,
                    ts.user_id AS tutor_id,
                    CONCAT(tu.first_name, ' ', tu.last_name) AS tutor_name,
                    tu.email AS tutor_email,
                    ts.student_id,
                    CONCAT(su.first_name, ' ', su.last_name) AS student_name,
                    su.email AS student_email,
                    s.year_id AS student_year_id,
                    y.name AS student_year
                FROM TutorStudents ts
                JOIN Users tu ON ts.user_id = tu.id
                JOIN Students s ON ts.student_id = s.id
                JOIN Users su ON s.user_id = su.id
                JOIN Years y ON s.year_id = y.id
            """)

            rows = cursor.fetchall()
            if not rows:
                return []

            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")



def sync_tutor_students_relationships(tutor_id: int, new_student_ids: List[int]) -> dict:
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            # Step 1: Fetch current student IDs
            cursor.execute("SELECT student_id FROM TutorStudents WHERE user_id = ?", (tutor_id,))
            current_student_ids = {row[0] for row in cursor.fetchall()}

            to_delete = current_student_ids - set(new_student_ids)
            to_insert = set(new_student_ids) - current_student_ids

            # Step 2: Delete removed relationships
            if to_delete:
                cursor.executemany(
                    "DELETE FROM TutorStudents WHERE user_id = ? AND student_id = ?",
                    [(tutor_id, sid) for sid in to_delete]
                )

            # Step 3: Add new relationships
            inserted_ids = []
            for sid in to_insert:
                try:
                    cursor.execute("""
                        INSERT INTO TutorStudents (user_id, student_id)
                        OUTPUT INSERTED.id
                        VALUES (?, ?)
                    """, (tutor_id, sid))
                    inserted_ids.append(cursor.fetchone()[0])
                except pyodbc.IntegrityError:
                    # Ignore duplicates or constraint violations gracefully
                    continue
                except Exception:
                    # Catch any unexpected insertion errors without breaking the sync
                    continue

            conn.commit()

            return {
                "message": "Tutor-student relationships synced.",
                "added_student_ids": list(to_insert),
                "removed_student_ids": list(to_delete),
            }

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")



def get_students_by_tutor(tutor_id: int):
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    ts.id,
                    ts.user_id AS tutor_id,
                    CONCAT(tu.first_name, ' ', tu.last_name) AS tutor_name,
                    tu.email AS tutor_email,
                    ts.student_id,
                    CONCAT(su.first_name, ' ', su.last_name) AS student_name,
                    su.email AS student_email,
                    s.year_id AS student_year_id,
                    y.name AS student_year
                FROM TutorStudents ts
                JOIN Users tu ON ts.user_id = tu.id
                JOIN Students s ON ts.student_id = s.id
                JOIN Users su ON s.user_id = su.id
                JOIN Years y ON s.year_id = y.id
                WHERE ts.user_id = ?
            """, (tutor_id,))

            rows = cursor.fetchall()
            if not rows:
                return []

            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")



def add_tutor_student(user_id: int, student_id: int) -> dict:
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            # Check user has Peer Tutor role
            cursor.execute("""
                SELECT 1 FROM UserRoles ur
                JOIN Roles r ON ur.role_id = r.id
                WHERE ur.user_id = ? AND r.role_name = 'Peer Tutor'
            """, (user_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=400, detail="User is not a Peer Tutor.")

            # Check for existing relationship
            cursor.execute("""
                SELECT 1 FROM TutorStudents WHERE user_id = ? AND student_id = ?
            """, (user_id, student_id))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Tutor-student relationship already exists.")

            # Insert new relationship
            cursor.execute("""
                INSERT INTO TutorStudents (user_id, student_id)
                OUTPUT INSERTED.id
                VALUES (?, ?)
            """, (user_id, student_id))

            new_id = cursor.fetchone()[0]
            conn.commit()

            return {"id": new_id, "user_id": user_id, "student_id": student_id}

    except HTTPException:
        raise
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")



def delete_tutor_student_by_id(relationship_id: int) -> dict:
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM TutorStudents WHERE id = ?", (relationship_id,))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Tutor-student relationship not found.")
            
            conn.commit()
            return {"message": "Tutor-student relationship deleted successfully."}

    except HTTPException:
        raise
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
