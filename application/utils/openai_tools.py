# application/utils/openai_tools.py
from typing import Literal
from pydantic import BaseModel
import openai  # SDK top-level, not `from openai import OpenAI`

class EmitSectionArgs(BaseModel):
    key: Literal[
        "assignmentInstructionsHtml",
        "stepByStepPlanHtml",
        "myPlanChecklistHtml",
        "motivationalMessageHtml",
        "template.title",
        "template.bodyHtml",
        "promptsHtml",
        "supportTools.toolsHtml",
        "supportTools.aiPromptingHtml",
        "supportTools.aiPolicyHtml",
    ]
    html: str

EMIT_SECTION_TOOL = [
    openai.pydantic_function_tool(
        EmitSectionArgs,
        name="emit_section",
        description="Emit a completed section as soon as it is ready.",
    )
]
