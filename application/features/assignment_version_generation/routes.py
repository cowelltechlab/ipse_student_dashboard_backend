import datetime
from typing import List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from application.database.nosql_connection import get_cosmos_db_connection
from application.features.assignment_version_generation.assignment_context import build_prompt_for_version, versions_container
from application.features.assignment_version_generation.crud import handle_assignment_suggestion_generation, handle_assignment_version_generation
from application.features.auth.permissions import require_user_access


from application.features.assignment_version_generation.schemas import AssignmentGenerationOptionsResponse, AssignmentUpdateBody, AssignmentVersionGenerationResponse
from application.utils.gpt_client import stream_sections_with_tools

router = APIRouter()
DATABASE_NAME = "ai-prompt-storage"
CONTAINER_NAME = "ai-modified-assignments"
cosmos_client = get_cosmos_db_connection()
cosmos_container = cosmos_client.get_database_client(DATABASE_NAME).get_container_client(CONTAINER_NAME)



@router.get("/assignment-generation/{assignment_id}", response_model=AssignmentGenerationOptionsResponse)
def generate_assignment_options(assignment_id: int, _user=Depends(require_user_access)):
    
    return handle_assignment_suggestion_generation(assignment_id, _user["user_id"])


@router.post("/assignment-generation/{assignment_version_id}", response_model=AssignmentVersionGenerationResponse)
def generate_new_assignment_version(
    assignment_version_id: str,
    selected_options: List[str] = Body(...),
    additional_edit_suggestions: Optional[str] = Body("")
):
    return handle_assignment_version_generation(
        assignment_version_id,
        selected_options,
        additional_edit_suggestions or ""
    )
    
@router.post("/assignment-generation/{assignment_version_id}/stream")
def stream_assignment_version(
    assignment_version_id: str,
    selected_options: list[str] = Body(...),
    additional_edit_suggestions: str | None = Body("")
):
    messages, persist_ctx = build_prompt_for_version(
        assignment_version_id=assignment_version_id,
        selected_options=selected_options,
        additional_edit_suggestions=additional_edit_suggestions or ""
    )

    def persist_final(obj: dict):
        # Write final JSON to Cosmos on stream completion
        version_doc = persist_ctx["version_doc"]
        version_doc["selected_options"] = persist_ctx["selected_options"]
        version_doc["extra_ideas_for_changes"] = persist_ctx["additional_edit_suggestions"]
        version_doc["finalized"] = False
        version_doc["final_generated_content"] = {"json_content": obj}
        version_doc["date_modified"] = datetime.datetime.utcnow().isoformat()
        versions_container.replace_item(item=version_doc["id"], body=version_doc)

    def event_source():
        for frame in stream_sections_with_tools(
            messages,
            model="gpt-4o-2024-08-06",
            on_complete=persist_final
        ):

            yield frame


    return StreamingResponse(event_source(), media_type="text/event-stream")



# @router.put("/assignment-generation/{assignment_version_id}", response_model=AssignmentVersionGenerationResponse)
# def update_assignment_version(assignment_version_id: str, body: AssignmentUpdateBody, _user=Depends(require_user_access)):
#     return handle_assignment_version_update(assignment_version_id, body.updated_json_content)
