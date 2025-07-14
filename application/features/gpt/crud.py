from .gpt_connection import get_gpt_response

def process_gpt_prompt(prompt: str, model: str = "gpt-3.5-turbo") -> str:
    # You could add extra processing here if needed
    return get_gpt_response(prompt, model)

def summarize_strengths(strengths: list[str]) -> str:
    prompt = f"Summarize these strengths in one sentence: {', '.join(strengths)}"
    return process_gpt_prompt(prompt, model="gpt-4")

def summarize_short_term_goals(short_term: str) -> str:
    prompt = f"Summarize these short term goals concisely: Short-term goal: {short_term}"
    return process_gpt_prompt(prompt, model="gpt-4")

def summarize_long_term_goals(long_term: str) -> str:
    prompt = f"Summarize these short term goals concisely, Long-term goal: {long_term}"
    return process_gpt_prompt(prompt, model="gpt-4")

def summarize_best_ways_to_learn(best_ways: str) -> str:
    prompt = f"Summarize these best ways to help a student into a comma separated list: {best_ways}"
    return process_gpt_prompt(prompt, model="gpt-4")

def generate_vision_statement(student_info: str) -> str:
    prompt = f"“Create a vision statement using plain, simple language for this student {student_info}, focusing on what they are working toward and how they will get there. Word it as a goal-discrepancy challenges, in line with Wehmeyer’s causal agency theory, NOT weakness. Instead, focus on tools, self-monitoring, and growth toward goals. Limit to no more than 40 words."
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
