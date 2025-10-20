import datetime
import os
from dotenv import load_dotenv
from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from application.database.nosql_connection import get_cosmos_db_connection
from application.features.assignment_version_generation.assignment_context import build_prompt_for_version, versions_container
from application.features.assignment_version_generation.crud import handle_assignment_suggestion_generation, handle_assignment_version_generation, handle_assignment_version_update, get_assignment_version_html, migrate_legacy_json_to_html, convert_json_to_html
from application.features.auth.permissions import require_user_access


from application.features.assignment_version_generation.schemas import AssignmentGenerationOptionsResponse, AssignmentGenerationRequest, AssignmentUpdateBody, AssignmentVersionGenerationResponse
from application.utils.gpt_client import stream_sections_with_tools

router = APIRouter()
load_dotenv()
DATABASE_NAME = os.getenv("COSMOS_DATABASE_NAME")

CONTAINER_NAME = "ai-modified-assignments"
cosmos_client = get_cosmos_db_connection()
cosmos_container = cosmos_client.get_database_client(DATABASE_NAME).get_container_client(CONTAINER_NAME)



@router.get("/assignment-generation/{assignment_id}", response_model=AssignmentGenerationOptionsResponse)
def generate_assignment_options(
    assignment_id: int,
    from_version: str = None,
    _user=Depends(require_user_access)
):
    return handle_assignment_suggestion_generation(assignment_id, _user["user_id"], from_version)


@router.post(
    "/assignment-generation/{assignment_version_id}",
    response_model=AssignmentVersionGenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a new assignment version HTML"
)
def generate_new_assignment_version(
    assignment_version_id: str,
    payload: AssignmentGenerationRequest = Body(
        ...,
        examples={
            "basic": {
                "summary": "Minimal",
                "value": {
                    "selected_options": ["outline", "checklist"],
                    "additional_edit_suggestions": ""
                }
            },
            "withIdeas": {
                "summary": "With extra ideas",
                "value": {
                    "selected_options": ["graphic organizer", "sentence starter"],
                    "additional_edit_suggestions": "Use Cornell notes and add due dates."
                }
            }
        }
    ),
):
    try:
        return handle_assignment_version_generation(
            assignment_version_id=assignment_version_id,
            selected_options=payload.selected_options,
            additional_edit_suggestions=payload.additional_edit_suggestions or ""
        )
    except HTTPException:
        raise
    except Exception as e:
        # Defensive catch to avoid leaking stack traces
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
    


# @router.post("/assignment-generation/{assignment_version_id}/stream")
# def stream_assignment_version(
#     assignment_version_id: str,
#     selected_options: list[str] = Body(...),
#     additional_edit_suggestions: str | None = Body("")
# ):
#     messages, persist_ctx = build_prompt_for_version(
#         assignment_version_id=assignment_version_id,
#         selected_options=selected_options,
#         additional_edit_suggestions=additional_edit_suggestions or ""
#     )

#     def persist_final(obj: dict):
#         version_doc = persist_ctx["version_doc"]
#         version_doc["selected_options"] = persist_ctx["selected_options"]
#         version_doc["additional_edit_suggestions"] = persist_ctx["additional_edit_suggestions"]
#         version_doc["finalized"] = False

#         # Convert JSON to HTML before saving
#         html_content = convert_json_to_html(obj)
#         version_doc["final_generated_content"] = {"html_content": html_content}

#         version_doc["date_modified"] = datetime.datetime.utcnow().isoformat() + "Z"
#         versions_container.replace_item(item=version_doc["id"], body=version_doc)


#     def event_source():
#         for frame in stream_sections_with_tools(
#             messages,
#             model=GPT_MODEL,
#             on_complete=persist_final
#         ):

#             yield frame


#     return StreamingResponse(event_source(), media_type="text/event-stream")



@router.put(
    "/assignment-generation/{assignment_version_id}",
    response_model=AssignmentVersionGenerationResponse
)
def update_assignment_version(
    assignment_version_id: str,
    body: AssignmentUpdateBody,
    _user = Depends(require_user_access)
):
    return handle_assignment_version_update(
        assignment_version_id,
        body.updated_html_content
    )


@router.get(
    "/assignment-generation/{assignment_version_id}/html",
    response_model=AssignmentVersionGenerationResponse,
    summary="Get assignment version HTML content (with legacy conversion)"
)
def get_assignment_version_html_content(
    assignment_version_id: str,
    _user = Depends(require_user_access)
):
    """Get HTML content for an assignment version, automatically converting legacy JSON if needed."""
    return get_assignment_version_html(assignment_version_id)


@router.post(
    "/assignment-generation/migrate",
    summary="Migrate legacy JSON content to HTML format"
)
def migrate_legacy_content(
    assignment_version_id: str = None,
    _user = Depends(require_user_access)
):
    """Migrate legacy JSON content to HTML format. If assignment_version_id is provided, migrates only that version."""
    return migrate_legacy_json_to_html(assignment_version_id)
