import json
import os
import re
from functools import lru_cache
from typing import Optional, List

from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

from application.features.gpt.crud import process_gpt_prompt_json, process_gpt_prompt_version_suggestion_json

load_dotenv()
GPT_MODEL = os.getenv("GPT_MODEL")
STORAGE_ACCOUNT_CONNECTION_STRING = os.getenv("STORAGE_ACCOUNT_CONNECTION_STRING")
LEARNING_PATHWAYS_CONTAINER_NAME = "learning-pathways-pictures"

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
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "for", "from",
    "how", "in", "into", "is", "it", "its", "of", "on", "or", "that", "the",
    "this", "to", "use", "using", "with", "you", "your"
}


def get_emoji_for_pathway(option: dict) -> str:
    """Pick an emoji for a learning pathway based on its name and description text."""
    name = (option.get("name") or "").lower()
    desc = (option.get("description") or "").lower()
    combined = f"{name} {desc}"
    for keywords, emoji in PATHWAY_EMOJI_KEYWORDS:
        if any(kw in combined for kw in keywords):
            return emoji
    return DEFAULT_PATHWAY_EMOJI


@lru_cache(maxsize=1)
def _get_learning_pathway_blob_names() -> List[str]:
    """
    Return the list of blob names in the learning pathways container.
    Cached so we don't hit storage on every call.
    """
    if not STORAGE_ACCOUNT_CONNECTION_STRING:
        return []

    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            STORAGE_ACCOUNT_CONNECTION_STRING
        )
        container_client = blob_service_client.get_container_client(
            LEARNING_PATHWAYS_CONTAINER_NAME
        )
        return [blob.name for blob in container_client.list_blobs()]
    except Exception:
        return []


@lru_cache(maxsize=512)
def _learning_pathway_blob_url(blob_name: str) -> Optional[str]:
    if not STORAGE_ACCOUNT_CONNECTION_STRING or not blob_name:
        return None
    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            STORAGE_ACCOUNT_CONNECTION_STRING
        )
        blob_client = blob_service_client.get_blob_client(
            container=LEARNING_PATHWAYS_CONTAINER_NAME,
            blob=blob_name,
        )
        return blob_client.url
    except Exception:
        return None


def _tokenize_for_image_matching(text: str) -> set[str]:
    tokens = set(re.findall(r"[a-z0-9]+", (text or "").lower()))
    return {t for t in tokens if t and t not in STOPWORDS and len(t) > 2}


def _score_blob_match(pathway_tokens: set[str], blob_name: str) -> int:
    blob_tokens = _tokenize_for_image_matching(blob_name.replace("_", " "))
    if not blob_tokens:
        return 0

    # Exact overlap is cheap and more stable than substring-only scoring.
    exact_overlap = pathway_tokens.intersection(blob_tokens)
    return len(exact_overlap) * 3


def assign_images_for_pathways(pathways: List[dict]) -> None:
    """
    Mutates pathway dicts in-place by setting image_url.
    Fast, deterministic matcher with simple diversity so all three cards
    do not collapse to the same image.
    """
    blob_names = _get_learning_pathway_blob_names()
    if not blob_names or not pathways:
        return

    used_blob_names: set[str] = set()
    blob_name_lookup = {name.lower(): name for name in blob_names}
    blob_stem_lookup = {name.lower().split(".")[0]: name for name in blob_names}
    for option in pathways:
        if option.get("image_url"):
            continue

        # Prefer the model's direct image choice when present.
        key_raw = (option.get("image_key") or "").strip().lower()
        if key_raw:
            chosen = blob_name_lookup.get(key_raw) or blob_stem_lookup.get(key_raw.split(".")[0])
            if chosen and chosen not in used_blob_names:
                option["image_url"] = _learning_pathway_blob_url(chosen)
                used_blob_names.add(chosen)
                continue

        text = f"{option.get('name', '')} {option.get('description', '')}"
        tokens = _tokenize_for_image_matching(text)
        if not tokens:
            continue

        best_name = None
        best_score = 0
        for name in blob_names:
            score = _score_blob_match(tokens, name)
            if name in used_blob_names:
                score -= 1  # slight diversity penalty; still allows reuse if clearly best

            if score > best_score:
                best_score = score
                best_name = name

        if best_name and best_score > 0:
            option["image_url"] = _learning_pathway_blob_url(best_name)
            used_blob_names.add(best_name)


def generate_assignment_modification_suggestions(student_profile: dict, assignment: dict, class_info: dict) -> dict:
    
    student_group = student_profile.get("group_type")
    blob_names = _get_learning_pathway_blob_names()
    available_images = "\n".join(f"- {name}" for name in blob_names) if blob_names else "- no-images-available"

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
            assignment_type=assignment.get("assignment_type", "N/A"),
            available_images=available_images,
        )

    elif student_group == "B":
        with open("application/features/assignment_version_generation/prompts/group_B_rec_prompt.txt", "r", encoding="utf-8") as f:
          template = f.read()
          prompt = template.format(
            class_name=class_info.get("class_name", "N/A"),
            assignment_title=assignment.get("title", "N/A"),
            assignment_content=assignment.get("content", "N/A"),
            assignment_type=assignment.get("assignment_type", "N/A"),
            available_images=available_images,
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