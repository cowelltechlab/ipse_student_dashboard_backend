import datetime
import os
from dotenv import load_dotenv
from fastapi import HTTPException
from application.database.nosql_connection import get_cosmos_db_connection
from application.features.assignment_version_generation.assignment_context import build_prompt_for_version
from gpt_client_nonstream import process_gpt_prompt_json


load_dotenv()
DATABASE_NAME = os.getenv("COSMOS_DATABASE_NAME")

PROFILE_CONTAINER_NAME = "ai-student-profile"
VERSIONS_CONTAINER_NAME = "ai-assignment-versions-v2"

_cosmos = get_cosmos_db_connection()
_db = _cosmos.get_database_client(DATABASE_NAME)
versions_container = _db.get_container_client(VERSIONS_CONTAINER_NAME)
profile_container  = _db.get_container_client(PROFILE_CONTAINER_NAME)


def handle_assignment_version_generation(
    assignment_version_id: str,
    selected_options: list[str],
    additional_edit_suggestions: str | None
):
    # Build messages + context (same as streaming)
    messages, ctx = build_prompt_for_version(
        assignment_version_id=assignment_version_id,
        selected_options=selected_options,
        additional_edit_suggestions=additional_edit_suggestions or ""
    )

    # If you want, remove the system tool header for non-streaming:
    # messages = [m for m in messages if m["role"] != "system"] + [{"role":"system","content":"Return one JSON object per the schema."}]

    # Call non-streaming structured output
    try:
        result = process_gpt_prompt_json(messages, model="gpt-4.1", max_out=16000)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GPT generation failed: {str(e)}")

    # Persist JSON
    version_doc = ctx["version_doc"]
    version_doc["selected_options"] = selected_options
    version_doc["extra_ideas_for_changes"] = additional_edit_suggestions or ""
    version_doc["finalized"] = False
    version_doc["final_generated_content"] = {"json_content": result}
    version_doc["date_modified"] = datetime.datetime.utcnow().isoformat()

    try:
        versions_container.replace_item(item=version_doc["id"], body=version_doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update version document: {str(e)}")

    return {
        "version_document_id": version_doc["id"],
        "json_content": result,
    }