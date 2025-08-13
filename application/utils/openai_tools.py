# application/utils/openai_tools.py
from typing import Literal
from pydantic import BaseModel
import openai  # using openai.pydantic_function_tool elsewhere

class EmitSectionArgs(BaseModel):
    # Only the NEW, allowed keys:
    key: Literal[
        "assignmentInstructionsHtml",
        "stepByStepPlanHtml",
        "promptsHtml",
        "supportTools.toolsHtml",
        "supportTools.aiPromptingHtml",
        "supportTools.aiPolicyHtml",
        "motivationalMessageHtml",
    ]
    html: str  # full HTML fragment (no outer <html>/<body>)

EMIT_SECTION_TOOL = [
    openai.pydantic_function_tool(
        EmitSectionArgs,
        name="emit_section",
        description=(
            "Emit one finished HTML fragment for a required section. "
            "Use only the allowed keys. Templates, when required, must be embedded "
            "inside supportTools.toolsHtml as <section data-block=\"template\"> with a single <pre>."
        ),
    )
]
