from application.database.mssql_connection import get_sql_db_connection


def get_all_tutor_students():
    conn = get_sql_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT 
                ts.id,
                ts.user_id AS tutor_id,
                CONCAT(tu.first_name, ' ', tu.last_name) AS tutor_name,
                tu.email AS tutor_email,
                ts.student_id,
                CONCAT(su.first_name, ' ', su.last_name) AS student_name,
                su.email AS student_email,
                y.name AS year_name
            FROM TutorStudents ts
            JOIN Users tu ON ts.user_id = tu.id
            JOIN Students s ON ts.student_id = s.id
            JOIN Users su ON s.user_id = su.id
            JOIN Years y ON s.year_id = y.id
        """)

        rows = cursor.fetchall()
        if not rows:
            return []
        
        tutor_students = []
        for row in rows:
            tutor_students.append(dict(zip([col[0] for col in cursor.description], row)))

        return tutor_students

def get_students_by_tutor(tutor_id: int):
    conn = get_sql_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT 
                ts.id,
                ts.user_id AS tutor_id,
                CONCAT(tu.first_name, ' ', tu.last_name) AS tutor_name,
                tu.email AS tutor_email,
                ts.student_id,
                CONCAT(su.first_name, ' ', su.last_name) AS student_name,
                su.email AS student_email,
                y.name AS year_name
            FROM TutorStudents ts
            JOIN Users tu ON ts.user_id = tu.id
            JOIN Students s ON ts.student_id = s.id
            JOIN Users su ON s.user_id = su.id
            JOIN Years y ON s.year_id = y.id
            WHERE ts.user_id = ?
        """, (tutor_id,))
        return [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]

def add_tutor_student(user_id: int, student_id: int):
    conn = get_sql_db_connection()
    with conn.cursor() as cursor:
        try:
            # Check user has Peer Tutor role
            cursor.execute("""
                SELECT 1 FROM UserRoles ur
                JOIN Roles r ON ur.role_id = r.id
                WHERE ur.user_id = ? AND r.role_name = 'Peer Tutor'
            """, (user_id,))
            if not cursor.fetchone():
                return {"error": "User is not a Peer Tutor."}

            # Check for existing relationship
            cursor.execute("""
                SELECT 1 FROM TutorStudents WHERE user_id = ? AND student_id = ?
            """, (user_id, student_id))
            if cursor.fetchone():
                return {"error": "Relationship already exists."}

            # Insert new relationship
            cursor.execute("""
                INSERT INTO TutorStudents (user_id, student_id)
                OUTPUT INSERTED.id
                VALUES (?, ?)
            """, (user_id, student_id))

            new_id = cursor.fetchone()[0]
            conn.commit()
            return {"id": new_id, "user_id": user_id, "student_id": student_id}

        except Exception as e:
            conn.rollback()
            return {"error": str(e)}


def delete_tutor_student_by_id(relationship_id: int):
    conn = get_sql_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            DELETE FROM TutorStudents WHERE id = ?
        """, (relationship_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return {"error": "Relationship not found."}
        return {"message": "Tutor-student relationship deleted."}