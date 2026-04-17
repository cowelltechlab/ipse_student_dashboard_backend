import json
import os
from typing import Optional

from dotenv import load_dotenv

from application.features.gpt.crud import process_gpt_prompt_json, process_gpt_prompt_version_suggestion_json

load_dotenv()
GPT_MODEL = os.getenv("GPT_MODEL")

# Keyword -> emoji for learning pathway display (matched against name + description)
PATHWAY_EMOJI_KEYWORDS = [
    (["visual", "video", "see", "watch", "diagram", "chart", "picture"], "👁️"),
    (["read", "reading", "text", "book", "written"], "📖"),
    (["listen", "audio", "podcast", "hear"], "👂"),
    (["write", "writing", "essay", "draft"], "✍️"),
    (["speak", "present", "presentation", "oral", "discuss"], "🎤"),
    (["group", "team", "together", "collaborative", "partner", "peer"], "👥"),
    (["hand", "hands-on", "practice", "do", "activity", "build", "create"], "✋"),
    (["think", "logic", "reason", "analyze", "reflect"], "🧠"),
    (["draw", "art", "design", "sketch"], "🎨"),
    (["goal", "plan", "step", "organize"], "🎯"),
    (["research", "find", "explore", "investigate"], "🔍"),
    (["tech", "digital", "computer", "online", "app"], "💻"),
    (["game", "play", "interactive"], "🎮"),
    (["story", "narrative", "role-play"], "📜"),
    (["movement", "move", "physical", "kinesthetic"], "🏃"),
    (["choice", "choose", "option", "preference"], "✅"),
]
DEFAULT_PATHWAY_EMOJI = "📚"


def get_emoji_for_pathway(option: dict) -> str:
    """Pick an emoji for a learning pathway based on its name and description text."""
    name = (option.get("name") or "").lower()
    desc = (option.get("description") or "").lower()
    combined = f"{name} {desc}"
    for keywords, emoji in PATHWAY_EMOJI_KEYWORDS:
        if any(kw in combined for kw in keywords):
            return emoji
    return DEFAULT_PATHWAY_EMOJI

def generate_assignment_modification_suggestions(student_profile: dict, assignment: dict, class_info: dict) -> dict:
    
    student_group = student_profile.get("group_type")

    if student_group == "A":
      with open("application/features/assignment_version_generation/prompts/group_A_rec_prompt.txt", "r", encoding="utf-8") as f:

        template = f.read()

        prompt = template.format(
            reading_level=student_profile.get("reading_level", "N/A"),
            writing_level=student_profile.get("writing_level", "N/A"),
            strengths=", ".join(student_profile.get("strengths", [])),
            challenges=", ".join(student_profile.get("challenges", [])),
            short_term_goals=student_profile.get("short_term_goals", "N/A"),
            long_term_goals=student_profile.get("long_term_goals", "N/A"),
            best_ways_to_help=", ".join(student_profile.get("best_ways_to_help", [])),
            hobbies_and_interests=student_profile.get("hobbies_and_interests", "N/A"),
            class_name=class_info.get("class_name", "N/A"),
            learning_goal=class_info.get("learning_goal", "N/A"),
            assignment_title=assignment.get("title", "N/A"),
            assignment_content=assignment.get("content", "N/A"),
            assignment_type=assignment.get("assignment_type", "N/A")
        )

    elif student_group == "B":
        with open("application/features/assignment_version_generation/prompts/group_B_rec_prompt.txt", "r", encoding="utf-8") as f:
          template = f.read()
          prompt = template.format(
            class_name=class_info.get("class_name", "N/A"),
            assignment_title=assignment.get("title", "N/A"),
            assignment_content=assignment.get("content", "N/A"),
            assignment_type=assignment.get("assignment_type", "N/A")
         )

#   TODO: Generate "else" case

    return process_gpt_prompt_version_suggestion_json(prompt, model=GPT_MODEL, override_max_tokens=8000)



def filter_selected_options(cosmos_doc: dict, selected_ids: list[str]):
    return [
        {
            "name": opt["name"],
            "description": opt["description"],
            "why_good_existing": opt["why_good_existing"],
            "why_good_growth": opt["why_good_growth"]
        }
        for opt in cosmos_doc.get("generated_options", [])
        if opt["internal_id"] in selected_ids
    ]



def generate_assignment(student_profile: dict, assignment: dict, class_info: dict, selected_changes: dict, additional_ideas_for_changes:Optional[str]):
    student_group = student_profile.get("group_type")

    # Filter and format selected options
    cosmos_doc = selected_changes.get("cosmos_doc")
    selected_ids = selected_changes.get("selected_ids", [])
    selected_options = filter_selected_options(cosmos_doc, selected_ids)

    # Build a JSON-like string to inject into prompt
    selected_options_str = json.dumps(selected_options, indent=2)

    if student_group == "A":
      with open("application/features/assignment_version_generation/prompts/group_A_version_generation_prompt.txt", "r", encoding="utf-8") as f:
        template = f.read()

        # Format prompt with all fields
        prompt = template.format(
            reading_level=student_profile.get("reading_level", "N/A"),
            writing_level=student_profile.get("writing_level", "N/A"),
            strengths=", ".join(student_profile.get("strengths", [])),
            challenges=", ".join(student_profile.get("challenges", [])),
            short_term_goals=student_profile.get("short_term_goals", "N/A"),
            long_term_goals=student_profile.get("long_term_goals", "N/A"),
            best_ways_to_help=", ".join(student_profile.get("best_ways_to_help", [])),
            hobbies_and_interests=student_profile.get("hobbies_and_interests", "N/A"),
            class_name=class_info.get("class_name", "N/A"),
            learning_goal=class_info.get("learning_goal", "N/A"),
            assignment_title=assignment.get("title", "N/A"),
            assignment_content=assignment.get("content", "N/A"),
            assignment_type=assignment.get("assignment_type", "N/A"),
            selected_options=selected_options_str,
            additional_ideas_for_changes=additional_ideas_for_changes or ""
        )

    elif student_group == "B":
      with open("application/features/assignment_version_generation/prompts/group_B_version_generation_prompt.txt", "r", encoding="utf-8") as f:
        template = f.read()

        # Format prompt with all fields
        prompt = template.format(
            
            class_name=class_info.get("class_name", "N/A"),
            assignment_title=assignment.get("title", "N/A"),
            assignment_content=assignment.get("content", "N/A"),
            assignment_type=assignment.get("assignment_type", "N/A"),
            selected_options=selected_options_str,
            additional_ideas_for_changes=additional_ideas_for_changes or ""
        )

    # TODO: Generate "else" case

       
    return process_gpt_prompt_json(prompt, model=GPT_MODEL, override_max_tokens=8000)