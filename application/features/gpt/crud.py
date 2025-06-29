from .gpt_connection import get_gpt_response

def process_gpt_prompt(prompt: str, model: str = "gpt-3.5-turbo") -> str:
    # You could add extra processing here if needed
    return get_gpt_response(prompt, model)

def summarize_strengths(strengths: list[str]) -> str:
    prompt = f"Summarize these strengths in one sentence: {', '.join(strengths)}"
    return process_gpt_prompt(prompt, model="gpt-4")

def summarize_goals(short_term: str, long_term: str) -> str:
    prompt = f"Summarize these goals concisely: Short-term goal: {short_term}, Long-term goal: {long_term}"
    return process_gpt_prompt(prompt, model="gpt-4")