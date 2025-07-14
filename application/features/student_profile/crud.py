from http.client import HTTPException
from typing import Optional
import uuid
from application.database.mssql_connection import get_sql_db_connection
from application.features.student_profile.schemas import StudentProfileCreate, StudentProfileUpdate
from application.database.nosql_connection import get_cosmos_db_connection  
from application.features.gpt.crud import summarize_best_ways_to_learn, summarize_long_term_goals, summarize_short_term_goals, summarize_strengths, generate_vision_statement

DATABASE_NAME = "ai-prompt-storage"
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
    conn = get_sql_db_connection()
    cursor = conn.cursor()
    try:
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
            cursor.execute(
                """
                INSERT INTO dbo.Students (user_id, year_id, reading_level, writing_level, active_status)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, ?, 1)
                """,
                (
                    data.user_id,
                    data.year_id,
                    data.reading_level,
                    data.writing_level,
                ),
            )
            student_id = cursor.fetchone()[0]

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

        # Commit SQL work now; Cosmos write will throw on error & can be retried
        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

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
    conn = get_sql_db_connection()
    cursor = conn.cursor()
    try:
        # Year name
        cursor.execute(
            """
            SELECT y.name
            FROM dbo.Students s
            INNER JOIN dbo.Years y ON s.year_id = y.id
            WHERE s.id = ?
            """,
            (student_id,),
        )
        year_row = cursor.fetchone()
        year_name = year_row[0] if year_row else None

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
    finally:
        conn.close()

    # ---------- Map to front‑end shape ----------
    summaries = doc.get("summaries", {})
    return {
        "student_id": student_id,
        "year_name": year_name,
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

def update_student_profile(student_id: int, patch: StudentProfileUpdate) -> dict:
    """
    • Update StudentClasses if 'classes' present
    • Patch Cosmos doc with provided fields
      Re‑run GPT summaries only for affected parts
    """
    # ---- SQL ----
    conn = get_sql_db_connection()
    cursor = conn.cursor()
    try:
        conn.autocommit = False

        if patch.classes is not None:
            # Clear & re‑insert current class list
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
                    for cls in patch.classes
                ],
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

     # ── Cosmos ────────────────────────────────────────────────────────────
    query = "SELECT * FROM c WHERE c.student_id = @sid"
    doc = next(
        container.query_items(
            query,
            parameters=[{"name": "@sid", "value": student_id}],
            enable_cross_partition_query=True,
        ),
        None,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Profile not found")

    summaries_changed = False

    if patch.strengths is not None:
        doc["strengths"] = patch.strengths
        doc.setdefault("summaries", {})["strength_short"] = summarize_strengths(
            patch.strengths
        )
        summaries_changed = True

    if patch.short_term_goals is not None:
        doc["short_term_goals"] = patch.short_term_goals
        doc.setdefault("summaries", {})[
            "short_term_goals"
        ] = summarize_short_term_goals(patch.short_term_goals)
        summaries_changed = True

    if patch.long_term_goals is not None:
        doc["long_term_goals"] = patch.long_term_goals
        doc.setdefault("summaries", {})[
            "long_term_goals"
        ] = summarize_long_term_goals(patch.long_term_goals)
        summaries_changed = True

    if patch.best_ways_to_help is not None:
        doc["best_ways_to_help"] = patch.best_ways_to_help
        doc.setdefault("summaries", {})[
            "best_ways_to_help"
        ] = summarize_best_ways_to_learn(patch.best_ways_to_help)
        summaries_changed = True

    if patch.challenges is not None:
        doc["challenges"] = patch.challenges

    if patch.hobbies_and_interests is not None:
        doc["hobbies_and_interests"] = patch.hobbies_and_interests

    # Regenerate vision only if a “core” field changed
    if summaries_changed:
        doc["vision"] = generate_vision_statement(str(doc))

    container.replace_item(item=doc["id"], body=doc)
    return doc


# def delete_profile(student_id: int):
#     profile = get_profile(student_id)
#     if not profile:
#         return None
#     container.delete_item(item=profile['id'], partition_key=profile['student_id'])
#     return {"deleted": True}
