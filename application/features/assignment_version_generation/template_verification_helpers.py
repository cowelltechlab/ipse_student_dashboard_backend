import json
import re
from fastapi import HTTPException

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

def _needs_template(selected_options_str: str, assignment_type: str | int | None) -> bool:
    s = (selected_options_str or "").lower()
    if any(k in s for k in TEMPLATE_TRIGGER_KEYWORDS):
        return True
    # assignment_type may be an id; convert known ids upstream if needed
    at = str(assignment_type or "").lower()
    return at in ASSIGNMENT_TYPES_REQUIRING_TEMPLATE

def _validate_and_order_result(raw: str, template_required: bool) -> dict:
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM output was not valid JSON: {e}")

    # Required top-level keys and order
    required_order = [
        "assignmentInstructionsHtml",
        "stepByStepPlanHtml",
        "promptsHtml",
        "supportTools",
        "motivationalMessageHtml",
    ]
    if list(data.keys()) != required_order:
        # Try to reorder if all keys present; else fail
        missing = [k for k in required_order if k not in data]
        extra = [k for k in data.keys() if k not in required_order]
        if missing or extra:
            raise HTTPException(status_code=500, detail=f"JSON keys mismatch. Missing: {missing}; Extra: {extra}")
        data = {k: data[k] for k in required_order}

    # supportTools structure and order
    st = data.get("supportTools")
    if not isinstance(st, dict):
        raise HTTPException(status_code=500, detail="supportTools must be an object")
    st_required_order = ["toolsHtml", "aiPromptingHtml", "aiPolicyHtml"]
    if list(st.keys()) != st_required_order:
        missing = [k for k in st_required_order if k not in st]
        extra = [k for k in st.keys() if k not in st_required_order]
        if missing or extra:
            raise HTTPException(status_code=500, detail=f"supportTools keys mismatch. Missing: {missing}; Extra: {extra}")
        st = {k: st[k] for k in st_required_order}
        data["supportTools"] = st

    # Simple HTML fragment checks (no <html>, <body>, <head>)
    def _is_fragment(value: str) -> bool:
        if not isinstance(value, str):
            return False
        lower = value.lower()
        return all(tag not in lower for tag in ("<html", "<body", "<head", "<!doctype"))

    for k in ["assignmentInstructionsHtml", "stepByStepPlanHtml", "promptsHtml", "motivationalMessageHtml"]:
        if not _is_fragment(data[k]):
            raise HTTPException(status_code=500, detail=f"{k} must be an HTML fragment (no outer wrappers)")
    for k in ["toolsHtml", "aiPromptingHtml", "aiPolicyHtml"]:
        if not _is_fragment(st[k]):
            raise HTTPException(status_code=500, detail=f"supportTools.{k} must be an HTML fragment (no outer wrappers)")

    # Template presence rule
    tools_html = st["toolsHtml"]
    if template_required:
        # exactly one template section with one pre
        sects = re.findall(r'<section[^>]*data-block="template"[^>]*>(.*?)</section>', tools_html, flags=re.S|re.I)
        if len(sects) != 1:
            raise HTTPException(status_code=500, detail="Template required but missing or multiple <section data-block=\"template\"> blocks")
        pre_blocks = re.findall(r"<pre>([\s\S]*?)</pre>", sects[0], flags=re.I)
        if len(pre_blocks) != 1:
            raise HTTPException(status_code=500, detail="Template section must contain exactly one <pre> block")
    else:
        # Must not include a template section
        if re.search(r'data-block="template"', tools_html, flags=re.I):
            raise HTTPException(status_code=500, detail="Template not required but template section was included")

    return data