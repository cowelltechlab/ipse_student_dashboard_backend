import openai

from application.features.gpt.crud import process_gpt_prompt

# TODO: get real prompt from Rachel
def generate_assignment_modification_suggestions(student_profile: dict, assignment: dict, class_info: dict) -> dict:
    prompt = f"""
You are an AI learning assistant. Given a student's profile and an assignment, return a JSON object with:

1. "skills_for_success" (1-2 sentence blurb describing skills needed to complete the assignment).
2. "learning_pathways": A list of 3 alternative ways to adapt or present the assignment. Each should contain:
    - title: A short title of the suggestion
    - description: 1-2 sentence description
    - reasons: Two brief, personalized reasons why this is suggested based on the student's profile

Respond only with JSON.

STUDENT PROFILE:
- Grade level: {student_profile.get("year_id")}
- Reading level: {student_profile.get("reading_level")}
- Writing level: {student_profile.get("writing_level")}
- Strengths: {", ".join(student_profile.get("strengths", []))}
- Challenges: {", ".join(student_profile.get("challenges", []))}
- Short-term goal: {student_profile.get("short_term_goals")}
- Long-term goal: {student_profile.get("long_term_goals")}
- Best ways to help: {", ".join(student_profile.get("best_ways_to_help", []))}
- Class learning goal: {class_info.get("learning_goal")}
- Class name: {class_info.get("class_name")}

ASSIGNMENT:
- Title: {assignment.get("title")}
- Content: {assignment.get("content")}
- Assignment type: {assignment.get("assignment_type")}
"""

    return process_gpt_prompt(prompt, model="gpt-4")

