import json
from typing import Optional
from .gpt_connection import get_gpt_response

def process_gpt_prompt(prompt: str, model: str = "gpt-3.5-turbo") -> str:
    # You could add extra processing here if needed
    return get_gpt_response(prompt, model)

def process_gpt_prompt_json(prompt: str, model: str = "gpt-4", override_max_tokens: Optional[int] = None
) -> dict:
    response_text = get_gpt_response(prompt, model=model, override_max_tokens=override_max_tokens).strip()

    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from GPT: {e}\nRaw content:\n{response_text}")

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
    prompt = f"""Create short, 1-2 sentence summary of these strengths
    using plain, simple language. Word challenges as what they student is working on,
    using goal-discrepancy gaps to be overcome, in line with Wehmeyer’s causal
    agency theory, NOT weaknesses. {', '.join(strengths)}"""
    return process_gpt_prompt(prompt, model="gpt-4")

def summarize_short_term_goals(short_term: str) -> str:
    prompt = f"""Create short, 1-2 sentence summary of these short term goals using plain,
    simple language. Word challenges as what they student is working on, using
    goal-discrepancy gaps to be overcome, in line with Wehmeyer’s causal agency theory,
    NOT weaknesses: {short_term}"""
    return process_gpt_prompt(prompt, model="gpt-4")

def summarize_long_term_goals(long_term: str) -> str:
    prompt = f"""Create short, 1-2 sentence summary of these long term goals using plain,
    simple language. Word challenges as what they student is working on, 
    using goal-discrepancy gaps to be overcome, in line with Wehmeyer’s causal agency theory, 
    NOT weaknesses. {long_term}"""
    return process_gpt_prompt(prompt, model="gpt-4")

def summarize_best_ways_to_learn(best_ways: str) -> str:
    prompt = f"""Create short, 1-2 sentence summary of these best ways for the student to learn
    using plain, simple language. Word challenges as what they student is working on,
    using goal-discrepancy gaps to be overcome, in line with Wehmeyer’s causal agency
    theory, NOT weaknesses. {best_ways}"""
    return process_gpt_prompt(prompt, model="gpt-4")

def generate_vision_statement(student_info: str) -> str:
    prompt = f"""Create a vision statement using plain, simple language for this student
    {student_info}, focusing on what they are working toward and how they will get there.
    Word it as a goal-discrepancy challenges, in line with Wehmeyer’s causal agency theory, 
    NOT weakness. Instead, focus on tools, self-monitoring, and growth toward goals. 
    Limit to no more than 40 words."""
    return process_gpt_prompt(prompt, model="gpt-4")

def generate_gpt_prompt(assignment, student, profile):
    return f"""
    You are an AI system following UDL guidelines from https://udlguidelines.cast.org/.

    1. Original Assignment: {assignment.html_content}

    2. UDL Recommendations:
    MME: {profile.get('udl_reasons', {}).get('Engagement', 'N/A')}
    MMR: {profile.get('udl_reasons', {}).get('Representation', 'N/A')}
    MMAE: {profile.get('udl_reasons', {}).get('Expression', 'N/A')}

    3. Requested Recommendations:
    - Use student strengths: {profile['strengths']}
    - Avoid student challenges: {profile['challenges']}

    4. Additional User Requests:
    - Adjust reading level to: {student.reading_level}
    - Adjust writing level to: {student.writing_level}

    ### Your Tasks
    A. Rewrite the assignment incorporating ONLY the above
    B. Reword based on reading/writing level

    Output:
    - Fully revised HTML assignment only. Do not output markdown or explanation.
    """
