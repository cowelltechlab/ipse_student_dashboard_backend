import os
from dotenv import load_dotenv
from fastapi import HTTPException
from typing import Optional
import uuid
import csv
import io
import json
from application.database.mssql_connection import get_sql_db_connection
from application.features.student_profile.schemas import StudentProfileCreate, StudentProfileUpdate
from application.database.nosql_connection import get_cosmos_db_connection
from application.features.gpt.crud import summarize_best_ways_to_learn, summarize_long_term_goals, summarize_short_term_goals, summarize_strengths, generate_vision_statement

import pyodbc

load_dotenv()
DATABASE_NAME = os.getenv("COSMOS_DATABASE_NAME")

CONTAINER_NAME = "ai-student-profile"

client = get_cosmos_db_connection()
db = client.get_database_client(DATABASE_NAME)
container = db.get_container_client(CONTAINER_NAME)

def create_or_update_profile(data: StudentProfileCreate) -> dict:
    """
    1. Update Users               (first / last name)
    2. Up‑sert Students           (year, reading / writing, active=1)
    3. Refresh StudentClasses     (delete‑all → insert current list)
    4. Up‑sert Cosmos doc with GPT‑generated summaries & vision
    Returns combined SQL + Cosmos payload (can become your response model).
    """

    # ----------  SQL section (transaction) ----------
   
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            conn.autocommit = False   # start explicit tx

            # 1.  Ensure user exists, then update names
            cursor.execute(
                "SELECT 1 FROM dbo.Users WHERE id = ?",
                (data.user_id,),
            )
            if cursor.fetchone() is None:
                raise HTTPException(
                    status_code=404, detail=f"User {data.user_id} not found"
                )

            cursor.execute(
                """
                UPDATE dbo.Users
                SET first_name = ?, last_name = ?
                WHERE id = ?
                """,
                (data.first_name, data.last_name, data.user_id),
            )

            # 2.  Up‑sert into Students table
            cursor.execute(
                "SELECT id FROM dbo.Students WHERE user_id = ?",
                (data.user_id,),
            )
            row = cursor.fetchone()
            if row:
                student_id = row[0]
                cursor.execute(
                    """
                    UPDATE dbo.Students
                    SET year_id = ?, reading_level = ?, writing_level = ?, active_status = 1
                    WHERE id = ?
                    """,
                    (
                        data.year_id,
                        data.reading_level,
                        data.writing_level,
                        student_id,
                    ),
                )
            else:
                row = cursor.execute(
                    """
                    SET NOCOUNT ON;

                    DECLARE @NewIds TABLE (id int);

                    INSERT INTO dbo.Students (user_id, year_id, reading_level, writing_level, active_status)
                    OUTPUT INSERTED.id INTO @NewIds(id)
                    VALUES (?, ?, ?, ?, 1);

                    SELECT id FROM @NewIds;
                    """,
                    (data.user_id, data.year_id, data.reading_level, data.writing_level),
                ).fetchone()

                if row[0] is None:
                    raise HTTPException(status_code=500, detail="Failed to create student record")
                
                student_id = int(row[0])
                conn.commit()

            # 3.  Refresh StudentClasses (remove‑then‑add)
            cursor.execute(
                "DELETE FROM dbo.StudentClasses WHERE student_id = ?",
                (student_id,),
            )
            insert_stmt = """
                INSERT INTO dbo.StudentClasses (student_id, class_id, learning_goal)
                VALUES (?, ?, ?)
            """
            cursor.executemany(
                insert_stmt,
                [
                    (student_id, cls.class_id, cls.class_goal)
                    for cls in data.classes
                ],
            )

            conn.commit()

    except Exception:
        raise


    # ----------  Cosmos section ----------
    
    # Build / update document
    # Does a doc already exist for this student?
    query = "SELECT * FROM c WHERE c.student_id = @sid"
    docs = list(
        container.query_items(
            query,
            parameters=[{"name": "@sid", "value": student_id}],
            enable_cross_partition_query=True,
        )
    )

    existing_doc = docs[0] if docs else None

    # ----- GPT summaries -----
    strength_short = summarize_strengths(data.strengths)
    goals_short_term = summarize_short_term_goals(data.short_term_goals)
    goals_long_term = summarize_long_term_goals(data.long_term_goals)
    best_help_short = summarize_best_ways_to_learn(data.best_ways_to_help)

    doc_body = {
        "id": existing_doc["id"] if existing_doc else str(uuid.uuid4()),
        "student_id": student_id,
        "strengths": data.strengths,
        "challenges": data.challenges,
        "hobbies_and_interests": data.likes_and_hobbies,
        "short_term_goals": data.short_term_goals,
        "long_term_goals": data.long_term_goals,
        "best_ways_to_help": data.best_ways_to_help,
        "summaries": {
            "strength_short": strength_short,
            "short_term_goals": goals_short_term,
            "long_term_goals": goals_long_term, 
            "best_ways_to_help": best_help_short,
        },
        "vision": generate_vision_statement(str(data)),
    }


    if existing_doc:
        container.replace_item(existing_doc, doc_body)
    else:
        container.create_item(body=doc_body)

    # Combine salient data for API response
    return {
        "student_id": student_id,
        "user_id": data.user_id,
        "cosmos_doc_id": doc_body["id"],
    }

def get_all_complete_profiles() -> list:
    """
    Get all student profiles by fetching all student IDs and calling get_complete_profile for each.
    Returns a list of complete profile dictionaries.
    """
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            # Get all student IDs that have active status
            cursor.execute("SELECT id FROM dbo.Students WHERE active_status = 1")
            student_ids = [row[0] for row in cursor.fetchall()]

    except pyodbc.Error as e:
        return [{"error": f"Database error: {str(e)}"}]
    except Exception as e:
        return [{"error": f"Unexpected error: {str(e)}"}]

    # Get complete profile for each student
    profiles = []
    for student_id in student_ids:
        profile = get_complete_profile(student_id)
        if profile and "error" not in profile:
            profiles.append(profile)

    return profiles
    

def get_complete_profile(student_id: int) -> Optional[dict]:
    """
    • Pull core attributes from Cosmos
    • Join SQL for year‑name & class list
    • Map keys to front‑end names
    """
    # ---------- Cosmos ----------
    query = "SELECT * FROM c WHERE c.student_id = @sid"
    cosmos_doc = list(
        container.query_items(
            query,
            parameters=[{"name": "@sid", "value": student_id}],
            enable_cross_partition_query=True,
        )
    )
    if not cosmos_doc:
        return None
    doc = cosmos_doc[0]

    # ---------- SQL ----------
  
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            # Year name and user name
            cursor.execute(
                """
                SELECT y.name, u.id, u.first_name, u.last_name, u.email, u.gt_email, u.profile_picture_url, s.ppt_embed_url, s.ppt_edit_url
                FROM dbo.Students s
                INNER JOIN dbo.Years y ON s.year_id = y.id
                INNER JOIN dbo.Users u ON s.user_id = u.id
                WHERE s.id = ?
                """,
                (student_id,),
            )
            row = cursor.fetchone()
            year_name = row[0] if row else None
            user_id = row[1] if row else None
            first_name = row[2] if row else None
            last_name = row[3] if row else None
            gmail = row[4] if row else None
            gt_email = row[5] if row else None
            profile_picture_url = row[6] if row else None
            ppt_embed_url = row[7] if row else None
            ppt_edit_url = row[8] if row else None

            # Classes
            cursor.execute(
                """
                SELECT sc.class_id, c.name, c.course_code, sc.learning_goal
                FROM dbo.StudentClasses sc
                INNER JOIN dbo.Classes c ON sc.class_id = c.id
                WHERE sc.student_id = ?
                """,
                (student_id,),
            )
            classes = [
                {
                    "class_id": cid,
                    "class_name": cname,
                    "course_code": ccode,
                    "learning_goal": goal,
                }
                for cid, cname, ccode, goal in cursor.fetchall()
            ]
    except pyodbc.Error as e:
        # Handle DB-related errors gracefully
        return {"error": f"Database error: {str(e)}"}
    except Exception as e:
        # Handle unexpected errors
        return {"error": f"Unexpected error: {str(e)}"}


    # ---------- Map to front‑end shape ----------
    summaries = doc.get("summaries", {})
    return {
        "student_id": student_id,
        "user_id": user_id,
        "first_name": first_name,
        "last_name": last_name,
        "email":gmail,
        "gt_email": gt_email,
        "profile_picture_url": profile_picture_url,
        "year_name": year_name,
        "ppt_embed_url": ppt_embed_url,
        "ppt_edit_url": ppt_edit_url,
        "classes": classes,
        "strengths": doc.get("strengths"),
        "challenges": doc.get("challenges"),
        "long_term_goals": doc.get("long_term_goals"),
        "short_term_goals": doc.get("short_term_goals"),
        "best_ways_to_help": doc.get("best_ways_to_help"),
        "hobbies_and_interests": doc.get("hobbies_and_interests"),
        "profile_summaries": {
            "strengths_short": summaries.get("strength_short"),
            "short_term_goals": summaries.get("short_term_goals"),
            "long_term_goals": summaries.get("long_term_goals"),
            "best_ways_to_help": summaries.get("best_ways_to_help"),
            "vision": doc.get("vision"),
        },
    }



def get_profile(student_id: int):
    query = "SELECT * FROM c WHERE c.student_id = @student_id"
    params = [{"name": "@student_id", "value": student_id}]
    items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    return items[0] if items else None


def update_student_profile(user_id: int, update_data: StudentProfileUpdate) -> dict:
   
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            conn.autocommit = False

            # Fetch student ID from user_id
            cursor.execute("SELECT id FROM dbo.Students WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"Student for user {user_id} not found")
            student_id = row[0]

            # Update Students table
            if update_data.year_id is not None:
                cursor.execute(
                    "UPDATE dbo.Students SET year_id = ? WHERE id = ?",
                    (update_data.year_id, student_id)
                )

            # Update classes if provided
            if update_data.classes is not None:
                cursor.execute("DELETE FROM dbo.StudentClasses WHERE student_id = ?", (student_id,))
                insert_stmt = """
                    INSERT INTO dbo.StudentClasses (student_id, class_id, learning_goal)
                    VALUES (?, ?, ?)
                """
                cursor.executemany(
                    insert_stmt,
                    [(student_id, cls.class_id, cls.class_goal) for cls in update_data.classes]
                )

            conn.commit()

    except HTTPException:
        raise

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


    # Cosmos update (partial merge)
    query = "SELECT * FROM c WHERE c.student_id = @sid"
    docs = list(
        container.query_items(
            query,
            parameters=[{"name": "@sid", "value": student_id}],
            enable_cross_partition_query=True,
        )
    )

    if not docs:
        raise HTTPException(status_code=404, detail="Cosmos student profile not found")

    doc = docs[0]

    # Only update provided fields
    if update_data.strengths is not None:
        doc["strengths"] = update_data.strengths
        doc["summaries"]["strength_short"] = summarize_strengths(update_data.strengths)

    if update_data.challenges is not None:
        doc["challenges"] = update_data.challenges

    if update_data.likes_and_hobbies is not None:
        doc["hobbies_and_interests"] = update_data.likes_and_hobbies

    if update_data.short_term_goals is not None:
        doc["short_term_goals"] = update_data.short_term_goals
        doc["summaries"]["short_term_goals"] = summarize_short_term_goals(update_data.short_term_goals)

    if update_data.long_term_goals is not None:
        doc["long_term_goals"] = update_data.long_term_goals
        doc["summaries"]["long_term_goals"] = summarize_long_term_goals(update_data.long_term_goals)

    if update_data.best_ways_to_help is not None:
        doc["best_ways_to_help"] = update_data.best_ways_to_help
        doc["summaries"]["best_ways_to_help"] = summarize_best_ways_to_learn(update_data.best_ways_to_help)

    doc["vision"] = generate_vision_statement(str(doc))  # update vision based on updated fields

    container.replace_item(item=doc, body=doc)

    return {
        "student_id": student_id,
        "user_id": user_id,
        "cosmos_doc_id": doc["id"],
    }


def get_prefill_profile(user_id: int) -> Optional[dict]:
    """
    Return basic user info, optional student_id, and Cosmos fields if any.
    Used for pre-filling the profile creation form.
    """
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()

            # --- Check if user exists ---
            cursor.execute(
                """
                SELECT first_name, last_name, email, gt_email, profile_picture_url
                FROM Users
                WHERE id = ?
                """,
                (user_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None

            first_name, last_name, email, gt_email, profile_picture_url = row

            # --- Get optional student_id and year_id ---
            cursor.execute(
                "SELECT id, year_id FROM Students WHERE user_id = ?", (user_id,)
            )
            row = cursor.fetchone()
            student_id = row[0] if row else None
            year_id = row[1] if row else None

            # --- Classes (only if student exists) ---
            classes = []
            if student_id:
                cursor.execute(
                    """
                    SELECT sc.class_id, sc.learning_goal
                    FROM dbo.StudentClasses sc
                    INNER JOIN dbo.Classes c ON sc.class_id = c.id
                    WHERE sc.student_id = ?
                    """,
                    (student_id,)
                )
                classes = [
                    {"class_id": cid, "class_goal": goal}
                    for cid, goal in cursor.fetchall()
                ]

            # --- Cosmos doc (only if student exists) ---
            cosmos_doc = {}
            if student_id:
                query = "SELECT * FROM c WHERE c.student_id = @sid"
                cosmos_docs = list(
                    container.query_items(
                        query,
                        parameters=[{"name": "@sid", "value": student_id}],
                        enable_cross_partition_query=True,
                    )
                )
                if cosmos_docs:
                    cosmos_doc = cosmos_docs[0]

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    return {
        "user_id": user_id,
        "student_id": student_id,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "gt_email": gt_email,
        "profile_picture_url": profile_picture_url,
        "year_id": year_id,
        "classes": classes,
        "strengths": cosmos_doc.get("strengths", []),
        "challenges": cosmos_doc.get("challenges", []),
        "long_term_goals": cosmos_doc.get("long_term_goals", ""),
        "short_term_goals": cosmos_doc.get("short_term_goals", ""),
        "best_ways_to_help": cosmos_doc.get("best_ways_to_help", []),
        "hobbies_and_interests": cosmos_doc.get("hobbies_and_interests", ""),
        "reading_level": cosmos_doc.get("reading_level", []),
        "writing_level": cosmos_doc.get("writing_level", []),
    }




def get_user_id_from_student(student_id: int) -> int:
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id FROM dbo.Students WHERE id = ?",
                (student_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Student not found")
            return row[0]

    except HTTPException:
        raise
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")



def update_user_profile_picture(user_id: int, blob_url: str) -> None:
   
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE dbo.Users SET profile_picture_url = ? WHERE id = ?",
                (blob_url, user_id)
            )
            conn.commit()

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")



def handle_post_ppt_urls(student_id: int, embed_url: str, edit_url: str) -> str:
    try:
        with get_sql_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE dbo.Students
                SET ppt_embed_url = ?, ppt_edit_url = ?
                WHERE id = ?
                """,
                (embed_url, edit_url, student_id)
            )

            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail=f"Student with id {student_id} not found")

            conn.commit()
            return "PPT URLs updated successfully."

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


def flatten_profile_for_export(profile: dict) -> dict:
    """
    Flatten nested profile data for CSV export.
    Converts lists and nested objects to string representations.
    """
    flattened = {}

    # Basic fields
    basic_fields = [
        'student_id', 'user_id', 'first_name', 'last_name', 'email', 'gt_email',
        'profile_picture_url', 'year_name', 'ppt_embed_url', 'ppt_edit_url'
    ]

    for field in basic_fields:
        flattened[field] = profile.get(field, '')

    # Convert list fields to comma-separated strings
    list_fields = ['strengths', 'challenges', 'best_ways_to_help']
    for field in list_fields:
        value = profile.get(field, [])
        flattened[field] = ', '.join(value) if isinstance(value, list) else str(value)

    # String fields
    string_fields = ['long_term_goals', 'short_term_goals', 'hobbies_and_interests']
    for field in string_fields:
        flattened[field] = profile.get(field, '')

    # Classes - convert to simplified string
    classes = profile.get('classes', [])
    if classes:
        class_names = [f"{cls.get('class_name', '')} ({cls.get('course_code', '')})" for cls in classes]
        flattened['classes'] = '; '.join(class_names)
        flattened['class_goals'] = '; '.join([cls.get('learning_goal', '') for cls in classes])
    else:
        flattened['classes'] = ''
        flattened['class_goals'] = ''

    # Profile summaries
    summaries = profile.get('profile_summaries', {})
    if summaries:
        flattened['strengths_summary'] = summaries.get('strengths_short', '')
        flattened['short_term_goals_summary'] = summaries.get('short_term_goals', '')
        flattened['long_term_goals_summary'] = summaries.get('long_term_goals', '')
        flattened['best_ways_to_help_summary'] = summaries.get('best_ways_to_help', '')
        flattened['vision_statement'] = summaries.get('vision', '')
    else:
        flattened['strengths_summary'] = ''
        flattened['short_term_goals_summary'] = ''
        flattened['long_term_goals_summary'] = ''
        flattened['best_ways_to_help_summary'] = ''
        flattened['vision_statement'] = ''

    return flattened


def export_profiles_to_csv() -> str:
    """
    Export all student profiles to CSV format.
    Returns CSV content as a string.
    """
    profiles = get_all_complete_profiles()

    if not profiles:
        return ""

    # Filter out any error profiles
    valid_profiles = [p for p in profiles if "error" not in p]

    if not valid_profiles:
        return ""

    # Flatten profiles for CSV
    flattened_profiles = [flatten_profile_for_export(profile) for profile in valid_profiles]

    # Create CSV in memory
    output = io.StringIO()
    if flattened_profiles:
        fieldnames = flattened_profiles[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flattened_profiles)

    return output.getvalue()


def export_profiles_to_json() -> str:
    """
    Export all student profiles to formatted JSON.
    Returns JSON content as a string.
    """
    profiles = get_all_complete_profiles()

    # Filter out any error profiles
    valid_profiles = [p for p in profiles if "error" not in p]

    return json.dumps(valid_profiles, indent=2, default=str)
