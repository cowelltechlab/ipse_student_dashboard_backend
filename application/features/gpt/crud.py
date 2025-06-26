from .gpt_connection import get_gpt_response

def process_gpt_prompt(prompt: str, model: str = "gpt-3.5-turbo") -> str:
    # You could add extra processing here if needed
    return get_gpt_response(prompt, model)
