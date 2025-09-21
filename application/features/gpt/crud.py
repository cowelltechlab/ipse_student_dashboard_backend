import json
from typing import Dict, List, Optional
from .gpt_connection import get_gpt_response
from openai import OpenAI

def process_gpt_prompt(prompt: str, model: str = "gpt-3.5-turbo") -> str:
    # You could add extra processing here if needed
    return get_gpt_response(prompt, model)


def process_gpt_prompt_version_suggestion_json(prompt: str, model: str = "gpt-4", override_max_tokens: Optional[int] = None
) -> dict:
    response_text = get_gpt_response(prompt, model=model, override_max_tokens=override_max_tokens).strip()

    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from GPT: {e}\nRaw content:\n{response_text}")


# gpt_client.py
client = OpenAI()

ASSIGNMENT_PACKAGE_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "assignmentInstructionsHtml": {"type": "string"},
        "stepByStepPlanHtml": {"type": "string"},
        "promptsHtml": {"type": "string"},
        "motivationalMessageHtml": {"type": "string"},
        "supportTools": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "toolsHtml": {"type": "string"},
                "aiPromptingHtml": {"type": "string"},
                "aiPolicyHtml": {"type": "string"}
            },
            "required": ["toolsHtml", "aiPromptingHtml", "aiPolicyHtml"]
        }
    },
    "required": [
        "assignmentInstructionsHtml",
        "stepByStepPlanHtml",
        "promptsHtml",
        "supportTools",
        "motivationalMessageHtml"
    ]
}




def process_gpt_prompt_json(
    messages: List[Dict],
    model: str = "gpt-4o-2024-08-06",
    override_max_tokens: int | None = None
) -> dict:
    resp = client.responses.create(
        model="gpt-4o-2024-08-06",
        input=messages,
        text={
            "format": {
                "type": "json_schema",
                "name": "AssignmentPackage",
                "strict": True,
                "schema": ASSIGNMENT_PACKAGE_JSON_SCHEMA,  # <-- raw JSON Schema dict
            }
        },
        temperature=0.2,
        max_output_tokens=8000,
    )
    obj = json.loads(resp.output_text)


    return obj


def process_gpt_prompt_html(
    prompt: str,
    model: str = "gpt-4.1",
    override_max_tokens: Optional[int] = None
) -> str:
    """
    Sends a prompt to GPT and returns the raw HTML string.
    Allows an optional override for max tokens.
    """
    response_text = get_gpt_response(prompt, model=model, override_max_tokens=override_max_tokens).strip()

    # Optionally, validate that the output is HTML
    if not response_text.lower().startswith("<!doctype html") and not response_text.lower().startswith("<html"):
        raise ValueError(f"Expected HTML but got unexpected content:\n{response_text[:200]}...")

    return response_text


def summarize_strengths(strengths: list[str]) -> str:
    prompt = f"""Write a short,  1 sentence summary (5-10 words AT MOST)  of these strengths in **first person**.
    Use plain, simple language (no greater than 4th grade level).
    Make it **motivating** and **future-focused**, framing challenges as what I am working on
    and strengths as tools for growth.
    Use Wehmeyer’s Causal Agency Theory to highlight purposeful action, self-direction, and confidence.
    Avoid listing weaknesses; instead, describe opportunities for growth.
    NO quotation marks on any phrases. Response should be output as plain text.
    Strengths: {', '.join(strengths)}
    """
    return process_gpt_prompt(prompt, model="gpt-4")

def summarize_short_term_goals(short_term: str) -> str:
    prompt = f"""Write a short, 1 sentence summary (5-10 words AT MOST) of these short-term goals in **first person**.
    Use plain, simple language (no greater than 4th grade level).
    Make it **motivating** and **goal-oriented**, framing challenges as what I am working on
    with a clear path forward.
    Follow Wehmeyer’s Causal Agency Theory by emphasizing purposeful action and self-monitoring.
    Avoid weaknesses; instead, highlight progress steps and confidence.
    Avoid adding quotation marks on any phrases. Response should be output as plain text.

    Short-term goals: {short_term}
    """
    return process_gpt_prompt(prompt, model="gpt-4")

def summarize_long_term_goals(long_term: str) -> str:
    prompt = f"""Write a short, 1 sentence summary (5-10 words AT MOST)  of these long-term goals in **first person**.
    Use plain, simple language (no greater than 4th grade level).
    Make it **motivating**, connecting what I’m learning now to my future dreams.
    Frame challenges as steps I am working through, showing determination and agency.
    Use Wehmeyer’s Causal Agency Theory to focus on self-determined action toward my vision.
    Avoid any weakness framing.
    Avoid adding quotation marks on any phrases. Response should be output as plain text.

    Long-term goals: {long_term}
    """
    return process_gpt_prompt(prompt, model="gpt-4")

def summarize_best_ways_to_learn(best_ways: str) -> str:
    prompt = f"""Write a short, 1 sentence summary (5-10 words AT MOST) of the best ways for me to learn, in **first person**.
    Use plain, simple language (no greater than 4th grade level).
    Make it **encouraging** and show that I understand how I learn best.
    Frame these as strategies I choose and use to reach my goals.
    Align with Wehmeyer’s Causal Agency Theory by highlighting purposeful use of resources and self-monitoring.
    Avoid weakness framing.
    Avoid adding quotation marks on any phrases. Response should be output as plain text.


    These should not be a numbered list, but instead a comma-separated list of phrases.
    Best ways to learn: {best_ways}
    """
    return process_gpt_prompt(prompt, model="gpt-4")

def generate_vision_statement(student_info: str) -> str:
    prompt = f"""Write a **first-person** vision statement, 1-2 sentences long (each sentence 5-7 words), using plain, simple language (no greater than 4th grade level).
    Make it **motivating**, connecting my present learning to my future dreams.
    Frame it as a positive challenge I am working on, with steps I will take.
    Follow Wehmeyer’s Causal Agency Theory by focusing on tools, self-direction, self-monitoring, and growth toward my goals.
    Avoid weaknesses, instead highlight confidence and purposeful action.
    NO quotation marks on any phrases. Response should be output as plain text.

    NEVER add emojis.

    Student info: {student_info}
    """
    return process_gpt_prompt(prompt, model="gpt-4")
