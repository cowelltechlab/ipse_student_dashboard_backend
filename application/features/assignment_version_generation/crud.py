import datetime
from fastapi import HTTPException
import pyodbc
import uuid
from application.database.mssql_connection import get_sql_db_connection
from application.features.assignment_version_generation.helpers import generate_assignment_modification_suggestions
from application.database.nosql_connection import get_cosmos_db_connection

# Constants
DATABASE_NAME = "ai-prompt-storage"
PROFILE_CONTAINER_NAME = "ai-student-profile"
VERSIONS_CONTAINER_NAME = "ai-assignment-versions"

# Cosmos client and containers
client = get_cosmos_db_connection()
db = client.get_database_client(DATABASE_NAME)
profile_container = db.get_container_client(PROFILE_CONTAINER_NAME)
versions_container = db.get_container_client(VERSIONS_CONTAINER_NAME)

def handle_assignment_suggestion_generation(assignment_id: int, modifier_id: int) -> dict:
    try:
        with get_sql_db_connection() as conn:
            with conn.cursor() as cursor:
                # 1. Fetch assignment
                cursor.execute("""
                    SELECT id, student_id, title, class_id, content, assignment_type_id
                    FROM dbo.Assignments
                    WHERE id = ?
                """, (assignment_id,))
                row = cursor.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Assignment not found")

                assignment = {
                    "id": row[0],
                    "student_id": row[1],
                    "title": row[2],
                    "class_id": row[3],
                    "content": row[4],
                    "assignment_type": row[5],
                }
                student_id = assignment["student_id"]
                class_id = assignment["class_id"]

                # 2. Fetch student info from SQL
                cursor.execute("""
                    SELECT year_id, reading_level, writing_level, group_type
                    FROM dbo.Students WHERE id = ?
                """, (student_id,))
                srow = cursor.fetchone()
                if not srow:
                    raise HTTPException(status_code=404, detail="Student not found")
                student_info = {
                    "year_id": srow[0],
                    "reading_level": srow[1],
                    "writing_level": srow[2],
                    "group_type": srow[3]
                }

                # 3. Fetch class goal
                cursor.execute("""
                    SELECT sc.learning_goal, c.name
                    FROM dbo.StudentClasses sc
                    JOIN dbo.Classes c ON sc.class_id = c.id
                    WHERE sc.student_id = ? AND sc.class_id = ?
                """, (student_id, class_id))
                crow = cursor.fetchone()
                class_info = {
                    "learning_goal": crow[0] if crow else "N/A",
                    "class_name": crow[1] if crow else "N/A"
                }

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected database error: {str(e)}")

    # 4. Fetch student profile from CosmosDB
    try:
        profile_docs = list(profile_container.query_items(
            query="SELECT * FROM c WHERE c.student_id = @sid",
            parameters=[{"name": "@sid", "value": student_id}],
            enable_cross_partition_query=True
        ))
        if not profile_docs:
            raise HTTPException(status_code=404, detail="Student profile not found in CosmosDB")
        cosmos_profile = profile_docs[0]
        full_profile = {**student_info, **cosmos_profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CosmosDB query failed: {str(e)}")

    # 5. Generate GPT suggestions
    try:
        gpt_raw = generate_assignment_modification_suggestions(
            student_profile=full_profile,
            assignment=assignment,
            class_info=class_info
        )
        gpt_data = gpt_raw

        # Inject internal IDs into each learning pathway
        for idx, option in enumerate(gpt_data.get("learning_pathways", []), start=1):
            option["internal_id"] = f"opt_{idx}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GPT generation failed: {str(e)}")

    # 6. Determine next version number from CosmosDB
    try:
        existing_versions = list(versions_container.query_items(
            query="SELECT VALUE c.version_number FROM c WHERE c.assignment_id = @aid",
            parameters=[{"name": "@aid", "value": assignment_id}],
            enable_cross_partition_query=True
        ))
        next_version = max(existing_versions or [0]) + 1
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching version numbers: {str(e)}")

    # 7. Save new version to CosmosDB
    try:
        doc_id = str(uuid.uuid4())
        new_doc = {
            "id": doc_id,
            "assignment_id": assignment_id,
            "modifier_id": modifier_id,
            "student_id": student_id,
            "version_number": next_version,
            "generated_options": gpt_data.get("learning_pathways", []),
            "skills_for_success": gpt_data.get("skills_for_success"),
            "finalized": False,
            "date_modified": datetime.datetime.utcnow().isoformat()
        }
        versions_container.create_item(body=new_doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving new version: {str(e)}")

    return {
        "skills_for_success": new_doc["skills_for_success"],
        "learning_pathways": new_doc["generated_options"],
        "version_document_id": doc_id
    }
