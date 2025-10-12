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


from application.features.gpt.crud import process_gpt_prompt_html


def convert_json_to_html(json_content: dict) -> str:
    """
    Convert legacy JSON assignment content to a single HTML block.

    Args:
        json_content: Legacy JSON object with structured HTML sections

    Returns:
        Combined HTML string with all sections
    """
    html_parts = []
    html_parts.append('<div class="assignment-content">')

    # Assignment Instructions
    if "assignmentInstructionsHtml" in json_content:
        html_parts.extend([
            '  <section class="instructions">',
            '    <h2>Assignment Instructions</h2>',
            f'    {json_content["assignmentInstructionsHtml"]}',
            '  </section>'
        ])

    # Step-by-Step Plan
    if "stepByStepPlanHtml" in json_content:
        html_parts.extend([
            '  <section class="plan">',
            '    <h2>Step-by-Step Plan</h2>',
            f'    {json_content["stepByStepPlanHtml"]}',
            '  </section>'
        ])

    # Prompts
    if "promptsHtml" in json_content:
        html_parts.extend([
            '  <section class="prompts">',
            '    <h2>Prompts</h2>',
            f'    {json_content["promptsHtml"]}',
            '  </section>'
        ])

    # Support Tools
    support_tools = json_content.get("supportTools", {})
    if support_tools:
        html_parts.extend([
            '  <section class="support-tools">',
            '    <h2>Tools and Resources</h2>'
        ])

        if "toolsHtml" in support_tools:
            html_parts.append(f'    {support_tools["toolsHtml"]}')

        if "aiPromptingHtml" in support_tools:
            html_parts.extend([
                '    <h3>AI Prompting Guide</h3>',
                f'    {support_tools["aiPromptingHtml"]}'
            ])

        if "aiPolicyHtml" in support_tools:
            html_parts.extend([
                '    <h3>AI Policy</h3>',
                f'    {support_tools["aiPolicyHtml"]}'
            ])

        html_parts.append('  </section>')

    # Motivational Message
    if "motivationalMessageHtml" in json_content:
        html_parts.extend([
            '  <section class="motivation">',
            '    <h2>Motivation</h2>',
            f'    {json_content["motivationalMessageHtml"]}',
            '  </section>'
        ])

    html_parts.append('</div>')

    return '\n'.join(html_parts)



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

def handle_assignment_suggestion_generation(assignment_id: int, modifier_id: int, from_version: str = None) -> dict:
    # If from_version is provided, retrieve the stored options and create a new version
    if from_version:
        try:
            version_doc = versions_container.read_item(
                item=from_version,
                partition_key=from_version
            )
        except Exception:
            raise HTTPException(status_code=404, detail="Version document not found")

        # Verify this version belongs to the requested assignment
        if version_doc.get("assignment_id") != assignment_id:
            raise HTTPException(status_code=400, detail="Version does not belong to this assignment")

        # Get the stored options and selected ones
        generated_options = version_doc.get("generated_options", [])
        selected_option_ids = version_doc.get("selected_options", [])
        additional_edit_suggestions = version_doc.get("additional_edit_suggestions", "")
        skills_for_success = version_doc.get("skills_for_success", "")
        student_id = version_doc.get("student_id")

        # Mark which options were selected
        for option in generated_options:
            option_id = option.get("internal_id")
            option["selected"] = option_id in selected_option_ids

        # Determine next version number from CosmosDB
        try:
            existing_versions = list(versions_container.query_items(
                query="SELECT VALUE c.version_number FROM c WHERE c.assignment_id = @aid",
                parameters=[{"name": "@aid", "value": assignment_id}],
                enable_cross_partition_query=True
            ))
            next_version = max(existing_versions or [0]) + 1
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching version numbers: {str(e)}")

        # Create new version document with the same options
        try:
            doc_id = str(uuid.uuid4())
            new_doc = {
                "id": doc_id,
                "assignment_id": assignment_id,
                "modifier_id": modifier_id,
                "student_id": student_id,
                "version_number": next_version,
                "generated_options": generated_options,
                "skills_for_success": skills_for_success,
                "finalized": False,
                "date_modified": datetime.datetime.utcnow().isoformat()
            }
            versions_container.create_item(body=new_doc)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving new version: {str(e)}")

        return {
            "skills_for_success": skills_for_success,
            "learning_pathways": generated_options,
            "version_document_id": doc_id,
            "additional_edit_suggestions": additional_edit_suggestions
        }

    # Otherwise, proceed with normal generation flow
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
        "version_document_id": doc_id,
        "additional_edit_suggestions": ""
    }


def get_html_content_from_document(version_doc: dict) -> str | None:
    """
    Extract HTML content from version document, converting legacy JSON if needed.

    Args:
        version_doc: Version document from database

    Returns:
        HTML content string or None if no content found
    """
    final_content = version_doc.get("final_generated_content", {})

    # Check for new HTML format first
    if "html_content" in final_content:
        return final_content["html_content"]

    # Check for legacy JSON format
    if "json_content" in final_content:
        json_content = final_content["json_content"]
        # Convert JSON to HTML
        html_content = convert_json_to_html(json_content)

        # Update the document to use HTML format (migrate on-the-fly)
        version_doc["final_generated_content"] = {"html_content": html_content}
        try:
            versions_container.replace_item(item=version_doc["id"], body=version_doc)
        except Exception as e:
            # If migration fails, just return the converted HTML without persisting
            pass

        return html_content

    # Check for very old format with direct HTML fields
    if "generated_html" in final_content or "raw_text" in final_content:
        return final_content.get("generated_html") or final_content.get("raw_text")

    return None


def handle_assignment_version_generation(
    assignment_version_id: str,
    selected_options: list[str],
    additional_edit_suggestions: str | None
):
    # Build messages + context for HTML generation
    messages, ctx = build_prompt_for_version(
        assignment_version_id=assignment_version_id,
        selected_options=selected_options,
        additional_edit_suggestions=additional_edit_suggestions or "",
        for_stream=False
    )

    # Call HTML generation model
    try:
        # Convert messages to a single prompt string for HTML generation
        prompt = "\n".join([msg["content"] for msg in messages if msg["role"] == "user"])
        result_html = process_gpt_prompt_html(
            prompt=prompt,
            model="gpt-4o",
            override_max_tokens=16000,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GPT generation failed: {str(e)}")

    version_doc = ctx["version_doc"]
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
    version_doc["additional_edit_suggestions"] = additional_edit_suggestions or ""
    version_doc["finalized"] = False
    version_doc["final_generated_content"] = {
        "html_content": result_html
    }
    version_doc["date_modified"] = current_timestamp

    try:
        versions_container.replace_item(item=version_doc["id"], body=version_doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update version document: {str(e)}")

    return {
        "version_document_id": version_doc["id"],
        "html_content": result_html,
    }




# For PUT endpoint. Replaces the full HTML content. Preserves the original.
def handle_assignment_version_update(assignment_version_id: str, updated_html: str) -> dict:
    # 1) Load
    try:
        version_doc = versions_container.read_item(
            item=assignment_version_id,
            partition_key=assignment_version_id
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Assignment version not found")

    # 2) Basic validation - ensure it's HTML content
    if not isinstance(updated_html, str) or not updated_html.strip():
        raise HTTPException(status_code=400, detail="Invalid HTML content provided")

    # 3) Preserve original content once (if not already saved) and save current version to history
    current_timestamp = datetime.datetime.utcnow().isoformat() + "Z"

    if "original_generated_content" not in version_doc:
        # Store the original generated content
        original_content = version_doc.get("final_generated_content")
        if original_content:
            version_doc["original_generated_content"] = original_content

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

    # 4) Write the new HTML
    version_doc["final_generated_content"] = {"html_content": updated_html}
    version_doc["finalized"] = False
    version_doc["date_modified"] = current_timestamp

    # 5) Save
    try:
        versions_container.replace_item(item=version_doc["id"], body=version_doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update version document: {str(e)}")

    # 6) Return
    return {
        "version_document_id": version_doc["id"],
        "html_content": updated_html
    }


def get_assignment_version_html(assignment_version_id: str) -> dict:
    """
    Get the HTML content for an assignment version, converting legacy JSON if needed.

    Args:
        assignment_version_id: The ID of the assignment version

    Returns:
        Dictionary with version_document_id and html_content
    """
    try:
        version_doc = versions_container.read_item(
            item=assignment_version_id,
            partition_key=assignment_version_id
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Assignment version not found")

    html_content = get_html_content_from_document(version_doc)

    if html_content is None:
        raise HTTPException(status_code=404, detail="No content found for this assignment version")

    return {
        "version_document_id": version_doc["id"],
        "html_content": html_content
    }


def migrate_legacy_json_to_html(assignment_version_id: str = None) -> dict:
    """
    Migrate legacy JSON content to HTML format.

    Args:
        assignment_version_id: Optional specific version to migrate. If None, migrates all legacy versions.

    Returns:
        Migration results summary
    """
    migrated_count = 0
    error_count = 0
    errors = []

    if assignment_version_id:
        # Migrate specific version
        try:
            version_doc = versions_container.read_item(
                item=assignment_version_id,
                partition_key=assignment_version_id
            )

            final_content = version_doc.get("final_generated_content", {})
            if "json_content" in final_content and "html_content" not in final_content:
                html_content = convert_json_to_html(final_content["json_content"])
                version_doc["final_generated_content"] = {"html_content": html_content}
                version_doc["date_modified"] = datetime.datetime.utcnow().isoformat() + "Z"

                versions_container.replace_item(item=version_doc["id"], body=version_doc)
                migrated_count = 1

        except Exception as e:
            error_count = 1
            errors.append(f"Error migrating {assignment_version_id}: {str(e)}")

    else:
        # Migrate all legacy versions
        try:
            # Query for documents with legacy JSON format
            legacy_docs = list(versions_container.query_items(
                query="SELECT * FROM c WHERE IS_DEFINED(c.final_generated_content.json_content) AND NOT IS_DEFINED(c.final_generated_content.html_content)",
                enable_cross_partition_query=True
            ))

            for doc in legacy_docs:
                try:
                    json_content = doc["final_generated_content"]["json_content"]
                    html_content = convert_json_to_html(json_content)

                    doc["final_generated_content"] = {"html_content": html_content}
                    doc["date_modified"] = datetime.datetime.utcnow().isoformat() + "Z"

                    versions_container.replace_item(item=doc["id"], body=doc)
                    migrated_count += 1

                except Exception as e:
                    error_count += 1
                    errors.append(f"Error migrating {doc.get('id', 'unknown')}: {str(e)}")

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")

    return {
        "migrated_count": migrated_count,
        "error_count": error_count,
        "errors": errors[:10]  # Limit to first 10 errors
    }
