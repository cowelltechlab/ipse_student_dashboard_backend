# assignment_context.py
import json
import datetime
import pyodbc
from fastapi import HTTPException

from application.database.mssql_connection import get_sql_db_connection
from application.database.nosql_connection import get_cosmos_db_connection

DATABASE_NAME = "ai-prompt-storage"
PROFILE_CONTAINER_NAME = "ai-student-profile"
VERSIONS_CONTAINER_NAME = "ai-assignment-versions-v2"

_cosmos = get_cosmos_db_connection()
_db = _cosmos.get_database_client(DATABASE_NAME)
versions_container = _db.get_container_client(VERSIONS_CONTAINER_NAME)
profile_container  = _db.get_container_client(PROFILE_CONTAINER_NAME)



def load_assignment_context(assignment_version_id: str):
    # Version doc
    try:
        version_doc = versions_container.read_item(
            item=assignment_version_id, partition_key=assignment_version_id
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Assignment version not found")

    assignment_id = version_doc["assignment_id"]
    student_id = version_doc["student_id"]

    # SQL: assignment, student, class
    try:
        with get_sql_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, title, class_id, content, assignment_type_id
                    FROM dbo.Assignments WHERE id = ?
                """, (assignment_id,))
                row = cursor.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Assignment not found")
                assignment = {
                    "id": row[0], "title": row[1], "class_id": row[2],
                    "content": row[3], "assignment_type": row[4]
                }

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
                    "group_type": srow[3],
                }

                cursor.execute("""
                    SELECT sc.learning_goal, c.name
                    FROM dbo.StudentClasses sc
                    JOIN dbo.Classes c ON sc.class_id = c.id
                    WHERE sc.student_id = ? AND sc.class_id = ?
                """, (student_id, assignment["class_id"]))
                crow = cursor.fetchone()
                class_info = {
                    "learning_goal": crow[0] if crow else "N/A",
                    "class_name": crow[1] if crow else "N/A",
                }
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"SQL error: {str(e)}")

    # Cosmos profile
    try:
        profile_docs = list(profile_container.query_items(
            query="SELECT * FROM c WHERE c.student_id = @sid",
            parameters=[{"name": "@sid", "value": student_id}],
            enable_cross_partition_query=True
        ))
        if not profile_docs:
            raise HTTPException(status_code=404, detail="Student profile not found in CosmosDB")
        full_profile = {**student_info, **profile_docs[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CosmosDB query failed: {str(e)}")

    return version_doc, assignment, class_info, full_profile


def filter_selected_options(cosmos_doc, selected_ids):
    # reuse your existing implementation; stubbed for completeness
    all_opts = cosmos_doc.get("options", [])
    by_id = {str(o.get("id")): o for o in all_opts}
    return [by_id[sid] for sid in selected_ids if sid in by_id]

def build_prompt_for_version(
    assignment_version_id: str,
    selected_options: list[str],
    additional_edit_suggestions: str | None = "",
    for_stream: bool = True
):
    # Load context
    version_doc, assignment, class_info, full_profile = load_assignment_context(assignment_version_id)

    # Selected options JSON
    selected = filter_selected_options(version_doc, selected_options)
    selected_options_str = json.dumps(selected, indent=2)

    # Choose group A/B template file
    group = full_profile.get("group_type")
    if group == "A":
        with open("application/features/assignment_version_generation/prompts/group_A_version_generation_prompt.txt", "r", encoding="utf-8") as f:
            template = f.read()
        user_prompt = template.format(
            reading_level=full_profile.get("reading_level", "N/A"),
            writing_level=full_profile.get("writing_level", "N/A"),
            strengths=", ".join(full_profile.get("strengths", [])),
            challenges=", ".join(full_profile.get("challenges", [])),
            short_term_goals=full_profile.get("short_term_goals", "N/A"),
            long_term_goals=full_profile.get("long_term_goals", "N/A"),
            best_ways_to_help=", ".join(full_profile.get("best_ways_to_help", [])),
            hobbies_and_interests=full_profile.get("hobbies_and_interests", "N/A"),
            class_name=class_info.get("class_name", "N/A"),
            learning_goal=class_info.get("learning_goal", "N/A"),
            assignment_title=assignment.get("title", "N/A"),
            assignment_content=assignment.get("content", "N/A"),
            assignment_type=assignment.get("assignment_type", "N/A"),
            selected_options=selected_options_str,
            additional_ideas_for_changes=additional_edit_suggestions or ""
        )
    else:
        with open("application/features/assignment_version_generation/prompts/group_B_version_generation_prompt.txt", "r", encoding="utf-8") as f:
            template = f.read()
        user_prompt = template.format(
            class_name=class_info.get("class_name", "N/A"),
            assignment_title=assignment.get("title", "N/A"),
            assignment_content=assignment.get("content", "N/A"),
            assignment_type=assignment.get("assignment_type", "N/A"),
            selected_options=selected_options_str,
            additional_ideas_for_changes=additional_edit_suggestions or ""
        )

    # System header for tool-call streaming
    tool_stream_header = (
        """
       You must NOT write plain text to the user.

        Call the tool "emit_section" exactly once per finished section, in this order:
        1. assignmentInstructionsHtml
        2. stepByStepPlanHtml
        3. myPlanChecklistHtml
        4. motivationalMessageHtml
        5. template.title (only if template is required; otherwise SKIP—do not call)
        6. template.bodyHtml (only if template is required; otherwise SKIP—do not call)
        7. promptsHtml (only if open-ended; otherwise SKIP—do not call)
        8. supportTools.toolsHtml (only if helpful; otherwise SKIP—do not call)
        9. supportTools.aiPromptingHtml (only if helpful; otherwise SKIP—do not call)
        10. supportTools.aiPolicyHtml (only if helpful; otherwise SKIP—do not call)

        IMPORTANT: Emit ALL applicable tool calls within a SINGLE response. 
        Do NOT wait for tool results. Do NOT stop after the first call.
        After emitting one section, immediately emit the next, until all applicable sections are emitted in order.

        The first four keys (1–4) are REQUIRED and must all be emitted, in order.
        Each tool call must include the complete HTML in field "html".
        Never emit partial fragments. Never include examples inside templates.
        Do not include extra fields or keys. Stop only after the last applicable section is emitted.

        """

    )

    # System header for final-JSON (non-stream) call
    json_header = (
        "Return one JSON object following the spec in the prompt (no tools). "
        "Keys must be in the exact order. Omit conditional keys when not applicable. "
        "All *Html values are valid HTML fragments (no outer HTML wrappers)."
    )

    messages = []
    persist_ctx = {
        "version_doc": version_doc,
        "selected_options": selected_options,
        "additional_edit_suggestions": additional_edit_suggestions or "",
    }
    if for_stream:
        messages.append({"role": "system", "content": tool_stream_header})
    else:
        messages.append({"role": "system", "content": json_header})
    messages.append({"role": "user", "content": user_prompt})
    return messages, persist_ctx
