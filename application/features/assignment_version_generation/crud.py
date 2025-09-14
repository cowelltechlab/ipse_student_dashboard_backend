import datetime
import json
import os
from dotenv import load_dotenv
from fastapi import HTTPException
import pyodbc
import uuid
from application.database.mssql_connection import get_sql_db_connection
from application.features.assignment_version_generation.assignment_context import build_prompt_for_version
from application.features.assignment_version_generation.helpers import generate_assignment, generate_assignment_modification_suggestions
from application.database.nosql_connection import get_cosmos_db_connection


from application.features.assignment_version_generation.template_verification_helpers import needs_template, validate_and_order_result
from application.features.gpt.crud import process_gpt_prompt_json



# Constants
load_dotenv()
DATABASE_NAME = os.getenv("COSMOS_DATABASE_NAME")

PROFILE_CONTAINER_NAME = "ai-student-profile"
VERSIONS_CONTAINER_NAME = "ai-assignment-versions-v2"

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
            "output_reasoning": gpt_data.get("output_reasoning"),
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


def handle_assignment_version_generation(
    assignment_version_id: str,
    selected_options: list[str],
    additional_edit_suggestions: str | None
):
    # Build messages + context using the JSON header (non-streaming)
    messages, ctx = build_prompt_for_version(
        assignment_version_id=assignment_version_id,
        selected_options=selected_options,
        additional_edit_suggestions=additional_edit_suggestions or "",
        for_stream=False,  # IMPORTANT: ensures json_header is used
    )

    # Call non-streaming structured output model
    try:
        result_text = process_gpt_prompt_json(
            messages=messages,
            model="gpt-4o-2024-08-06",
            override_max_tokens=16000,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GPT generation failed: {str(e)}")

    # Determine if a template is required (pre-validate)
    version_doc = ctx["version_doc"]
    assignment_type = version_doc.get("assignment_type") or ""  # or map id->name upstream
    selected_options_str = json.dumps(ctx.get("selected_options", []), indent=2)
    template_required = needs_template(selected_options_str, assignment_type)

    # Validate schema, order, and template rules
    data_obj = validate_and_order_result(result_text, template_required)

    # Persist JSON with version history
    current_timestamp = datetime.datetime.utcnow().replace(tzinfo=None).isoformat() + "Z"

    # Save current version to history before updating (if it exists)
    if "final_generated_content" in version_doc and version_doc["final_generated_content"]:
        # Initialize generation_history if it doesn't exist
        if "generation_history" not in version_doc:
            version_doc["generation_history"] = []

        # Add current version to history
        current_version = version_doc["final_generated_content"].copy()
        current_version["timestamp"] = version_doc.get("date_modified", current_timestamp)
        current_version["generation_type"] = "regeneration"  # This is a regeneration of existing content
        version_doc["generation_history"].append(current_version)

    version_doc["selected_options"] = selected_options
    # Choose a single, consistent field name:
    version_doc["additional_edit_suggestions"] = additional_edit_suggestions or ""
    version_doc["finalized"] = False
    version_doc["final_generated_content"] = {
        "json_content": data_obj,
        "raw_text": result_text,
    }
    version_doc["date_modified"] = current_timestamp

    try:
        versions_container.replace_item(item=version_doc["id"], body=version_doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update version document: {str(e)}")

    return {
        "version_document_id": version_doc["id"],
        "json_content": data_obj,
    }




# For PUT endpoint. Replaces the full JSON object. Preserves the original once.
def handle_assignment_version_update(assignment_version_id: str, updated_json_content: dict) -> dict:
    # 1) Load
    try:
        version_doc = versions_container.read_item(
            item=assignment_version_id,
            partition_key=assignment_version_id
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Assignment version not found")

    # 2) Decide if a template is required for this assignment
    #    Reuse your same trigger logic from generation time.
    selected_options = version_doc.get("selected_options", [])
    assignment_type   = version_doc.get("assignment_type") or version_doc.get("assignment", {}).get("assignment_type")
    # Normalize to string list for the helper
    try:
        selected_options_str = json.dumps(selected_options, indent=2)
    except Exception:
        selected_options_str = str(selected_options)

    # If you defined _needs_template elsewhere, import and reuse it.
    template_required = needs_template(selected_options_str, assignment_type)

    # 3) Validate and normalize order
    validated = validate_and_order_result(updated_json_content, template_required)

    # 4) Preserve original JSON once (if not already saved) and save current version to history
    current_timestamp = datetime.datetime.utcnow().isoformat() + "Z"

    if "original_generated_json_content" not in version_doc:
        # Handle legacy docs that stored HTML instead of JSON
        legacy_html = (
            version_doc.get("final_generated_content", {}).get("html_content")
            if isinstance(version_doc.get("final_generated_content"), dict)
            else None
        )
        if legacy_html:
            version_doc["original_generated_html_content"] = legacy_html
        original_json = (
            version_doc.get("final_generated_content", {}).get("json_content")
            if isinstance(version_doc.get("final_generated_content"), dict)
            else None
        )
        if original_json is not None:
            version_doc["original_generated_json_content"] = original_json

    # Save current version to history before updating (if it exists)
    if "final_generated_content" in version_doc and version_doc["final_generated_content"]:
        # Initialize generation_history if it doesn't exist
        if "generation_history" not in version_doc:
            version_doc["generation_history"] = []

        # Add current version to history
        current_version = version_doc["final_generated_content"].copy()
        current_version["timestamp"] = version_doc.get("date_modified", current_timestamp)
        current_version["generation_type"] = "edit"  # This is a manual edit
        version_doc["generation_history"].append(current_version)

    # 5) Write the new JSON
    version_doc["final_generated_content"] = {"json_content": validated}
    version_doc["finalized"] = False
    version_doc["date_modified"] = current_timestamp

    # 6) Save
    try:
        versions_container.replace_item(item=version_doc["id"], body=version_doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update version document: {str(e)}")

    # 7) Return
    return {
        "version_document_id": version_doc["id"],
        "json_content": validated
    }
