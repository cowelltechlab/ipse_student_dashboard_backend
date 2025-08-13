# template_verification_helpers.py
from __future__ import annotations

import json
import re
from typing import Any
from collections.abc import Mapping

from fastapi import HTTPException
from pydantic import BaseModel  # <-- correct BaseModel

TEMPLATE_TRIGGER_KEYWORDS = {
    "graphic organizer", "organizer", "sentence starter", "sentence starters",
    "template", "template guide", "guide", "outline", "slide outline",
    "storyboard", "table", "two-column notes", "cornell notes", "checklist",
    "rubric", "frame", "frames", "frame sentence", "fill-in-the-blank",
    "scaffold", "timeline"
}

ASSIGNMENT_TYPES_REQUIRING_TEMPLATE = {
    "essay", "paper", "lab", "presentation", "slideshow", "poster",
    "research", "reflection", "reading response", "project", "portfolio"
}

def _to_plain(obj: Any) -> Any:
    """Normalize Pydantic models and mappings/lists to plain Python types."""
    if isinstance(obj, BaseModel):
        return obj.model_dump(exclude_unset=False, exclude_none=False, by_alias=False)
    if isinstance(obj, Mapping):
        return {k: _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_plain(v) for v in obj]
    return obj

def needs_template(selected_options_str: str, assignment_type: str | int | None) -> bool:
    s = (selected_options_str or "").lower()
    if any(k in s for k in TEMPLATE_TRIGGER_KEYWORDS):
        return True
    at = str(assignment_type or "").lower()
    return at in ASSIGNMENT_TYPES_REQUIRING_TEMPLATE

def validate_and_order_result(data_in: Any, template_required: bool) -> dict[str, Any]:
    """
    Accepts: JSON string, dict-like, or Pydantic model.
    Returns: normalized dict with enforced key order and validated fragments.
    """
    # 1) Parse/normalize to a plain dict
    try:
        if isinstance(data_in, str):
            data = json.loads(data_in)
        else:
            data = _to_plain(data_in)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM output was not valid JSON: {e}")

    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail=f"Expected object at top level, got {type(data).__name__}")

    # 2) Required top-level keys / order
    required_order = [
        "assignmentInstructionsHtml",
        "stepByStepPlanHtml",
        "promptsHtml",
        "supportTools",
        "motivationalMessageHtml",
    ]

    # First check presence; then reorder if the sets match but order differs.
    missing = [k for k in required_order if k not in data]
    extra = [k for k in data.keys() if k not in required_order]
    if missing or extra:
        raise HTTPException(
            status_code=500,
            detail=f"JSON keys mismatch. Missing: {missing}; Extra: {extra}"
        )

    if list(data.keys()) != required_order:
        data = {k: data[k] for k in required_order}

    # 3) supportTools structure / order
    st = data.get("supportTools")
    if not isinstance(st, dict):
        raise HTTPException(status_code=500, detail="supportTools must be an object")

    st_required_order = ["toolsHtml", "aiPromptingHtml", "aiPolicyHtml"]
    st_missing = [k for k in st_required_order if k not in st]
    st_extra = [k for k in st.keys() if k not in st_required_order]
    if st_missing or st_extra:
        raise HTTPException(
            status_code=500,
            detail=f"supportTools keys mismatch. Missing: {st_missing}; Extra: {st_extra}"
        )

    if list(st.keys()) != st_required_order:
        st = {k: st[k] for k in st_required_order}
        data["supportTools"] = st  # write back in order

    # 4) HTML fragment checks (no outer wrappers)
    def _is_fragment(value: str) -> bool:
        if not isinstance(value, str):
            return False
        lower = value.lower()
        return all(tag not in lower for tag in ("<html", "<body", "<head", "<!doctype"))

    for k in ["assignmentInstructionsHtml", "stepByStepPlanHtml", "promptsHtml", "motivationalMessageHtml"]:
        if not _is_fragment(data[k]):
            raise HTTPException(
                status_code=500,
                detail=f"{k} must be an HTML fragment (no outer wrappers)"
            )

    for k in ["toolsHtml", "aiPromptingHtml", "aiPolicyHtml"]:
        if not _is_fragment(st[k]):
            raise HTTPException(
                status_code=500,
                detail=f"supportTools.{k} must be an HTML fragment (no outer wrappers)"
            )

    # 5) Template rules
    tools_html = st["toolsHtml"]
    if template_required:
        # Exactly one template section containing exactly one <pre>
        sects = re.findall(
            r'<section[^>]*data-block="template"[^>]*>(.*?)</section>',
            tools_html, flags=re.S | re.I
        )
        if len(sects) != 1:
            raise HTTPException(
                status_code=500,
                detail='Template required but missing or multiple <section data-block="template"> blocks'
            )
        pre_blocks = re.findall(r"<pre>([\s\S]*?)</pre>", sects[0], flags=re.I)
        if len(pre_blocks) != 1:
            raise HTTPException(
                status_code=500,
                detail="Template section must contain exactly one <pre> block"
            )
    else:
        if re.search(r'data-block="template"', tools_html, flags=re.I):
            raise HTTPException(
                status_code=500,
                detail="Template not required but template section was included"
            )

    return data
