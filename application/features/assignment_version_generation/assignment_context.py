# assignment_context.py
import json
import datetime
import os
from dotenv import load_dotenv
import pyodbc
from fastapi import HTTPException

from application.database.mssql_connection import get_sql_db_connection
from application.database.nosql_connection import get_cosmos_db_connection

PROFILE_CONTAINER_NAME = "ai-student-profile"
VERSIONS_CONTAINER_NAME = "ai-assignment-versions-v2"

load_dotenv()
DATABASE_NAME = os.getenv("COSMOS_DATABASE_NAME")

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


def filter_selected_options(cosmos_doc: dict, selected_ids: list[str]):
    # Prefer generated_options; fall back to options for older docs
    opts = cosmos_doc.get("generated_options") or cosmos_doc.get("options") or []
    if not opts or not selected_ids:
        return [], list(map(str, selected_ids or []))

    # Detect the identifier field once
    id_field = None
    for candidate in ("internal_id", "id", "internalId", "option_id"):
        if opts and candidate in opts[0]:
            id_field = candidate
            break
    if id_field is None:
        return [], list(map(str, selected_ids))

    # Build map and normalize to str for reliable matching
    by_id = {str(o.get(id_field)): o for o in opts if id_field in o}

    # Preserve the order in selected_ids; skip unknowns
    picked = [by_id[sid] for sid in map(str, selected_ids) if sid in by_id]
    # missing = [sid for sid in map(str, selected_ids) if sid not in by_id]
    return picked


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

    # System header for tool-call streaming (updated to new schema)
    tool_stream_header = (
        """
        You must NOT write plain text to the user.

        Call the tool "emit_section" exactly once per finished section, in this order:
        1. assignmentInstructionsHtml           (REQUIRED)
        2. stepByStepPlanHtml                   (REQUIRED)
        3. promptsHtml                          (REQUIRED)
        4. supportTools.toolsHtml               (REQUIRED)
        5. supportTools.aiPromptingHtml         (REQUIRED)
        6. supportTools.aiPolicyHtml            (REQUIRED)
        7. motivationalMessageHtml              (REQUIRED)

        IMPORTANT EMISSION RULES
        • Emit ALL seven sections above within a SINGLE response.
        • Do NOT wait for tool results. Do NOT stop after the first call.
        • After emitting one section, immediately emit the next, until all are emitted in order.
        • Each tool call must include the complete HTML fragment in field "html".
        • Fragments must NOT include <!DOCTYPE>, <html>, <head>, or <body> wrappers.
        • Sentences should be concise (≤ 10–12 words). Grade-4 reading level. Adult, respectful tone.
        • Place emojis at the END of sentences (inside fragments).

        TEMPLATE RULES (embedded inside supportTools.toolsHtml ONLY)
        • If a template is REQUIRED (per prompt Template Trigger Rules), include exactly one block:
        <section data-block="template">
            <h3>Template</h3>
            <p>Use this blank template.</p>
            <pre>
            [TEMPLATE NAME]
            [SECTION 1]: ______________________
            [SECTION 2]: ______________________
            ...
            </pre>
        </section>
        • The <pre> contains only labels/placeholders; no examples or filled content.
        • Do NOT emit any separate template keys (e.g., no template.title, no template.bodyHtml).

        GRADING & DUE DATES
        • assignmentInstructionsHtml must include a short grading description tied to success skills and chosen options.
        • If due dates appear in inputs, repeat them in stepByStepPlanHtml and reference them in assignmentInstructionsHtml.

        CONTENT SAFETY & SCOPE
        • Do NOT identify or label weaknesses. Frame supports as solutions to a goal-discrepancy.
        • Preserve course technical terms exactly; add 2–5 word explanations when needed.
        • Keep outer JSON key order in mind (this stream prepares those fields).

        GROUP LOGIC (applies automatically based on the user message content)
        • If the user message includes student profile fields, you may reference strengths/goals
        without naming weaknesses, per rules.
        • If no student profile fields are present (Group B case), do NOT include or infer personal data.

        FINAL SELF-CHECK (before emitting the last section)
        • If Template Trigger Rules fired, confirm supportTools.toolsHtml contains one (1)
        <section data-block="template"> with a single <pre>.
        • Insert a final non-rendered HTML comment into supportTools.toolsHtml with:
        <!-- TEMPLATE_REQUIRED: yes|no ; TEMPLATE_TYPE: essay|presentation|lab|reading|project|other -->
        """
    )

    # System header for final-JSON (non-stream) call (kept in sync with new spec)
    json_header = (
        "Return one JSON object following the spec in the prompt (no tools). "
        "Keys must be in this exact order: "
        "assignmentInstructionsHtml, stepByStepPlanHtml, promptsHtml, supportTools, motivationalMessageHtml. "
        "Inside supportTools, include keys in this exact order: toolsHtml, aiPromptingHtml, aiPolicyHtml. "
        "Omit no keys (all are required). "
        "All *Html values are valid HTML fragments (no outer HTML wrappers). "
        "If a template is required, it must appear only inside supportTools.toolsHtml as a single "
        "<section data-block=\"template\"> containing exactly one <pre> block. "
        "Sentences ≤ 10–12 words, Grade-4 reading level, respectful adult tone, emojis at sentence ends."
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
