import openai

from application.features.gpt.crud import process_gpt_prompt_json

# TODO: get real prompt from Rachel
def generate_assignment_modification_suggestions(student_profile: dict, assignment: dict, class_info: dict) -> dict:
    prompt = prompt = f"""
You are an AI learning assistant. Your task is to analyze a student's profile and a class assignment, then generate JSON output that helps personalize the assignment.

### OUTPUT FORMAT
Respond ONLY with a valid JSON object using the following schema:

{{
  "skills_for_success": "string (1-2 sentences)",
  "learning_pathways": [
    {{
      "title": "string",
      "description": "string (1-2 sentences)",
      "reasons": ["string", "string"]
    }},
    ... (total of 3 items)
  ]
}}

### STUDENT PROFILE
- Grade level: {student_profile.get("year_id")}
- Reading level: {student_profile.get("reading_level")}
- Writing level: {student_profile.get("writing_level")}
- Strengths: {", ".join(student_profile.get("strengths", []))}
- Challenges: {", ".join(student_profile.get("challenges", []))}
- Short-term goal: {student_profile.get("short_term_goals")}
- Long-term goal: {student_profile.get("long_term_goals")}
- Best ways to help: {", ".join(student_profile.get("best_ways_to_help", []))}

### CLASS INFO
- Class name: {class_info.get("class_name")}
- Class learning goal: {class_info.get("learning_goal")}

### ASSIGNMENT
- Title: {assignment.get("title")}
- Content: {assignment.get("content")}
- Assignment type: {assignment.get("assignment_type")}

Do not include explanations or any extra commentary.
Only return the JSON object that matches the schema exactly.
"""


    return process_gpt_prompt_json(prompt, model="gpt-4")


