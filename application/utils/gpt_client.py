# gpt_client.py
import json
from typing import Iterator, Callable, List, Dict, Any
from openai import OpenAI
from application.utils.openai_tools import EMIT_SECTION_TOOL

client = OpenAI()

def _buf_key(ev) -> str | None:
    # Works across event shapes
    return getattr(ev, "item_id", None) or getattr(getattr(ev, "item", None), "id", None)

def _parse_args(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}

def stream_sections_with_tools(
    messages: List[Dict[str, Any]],
    model: str = "gpt-5-mini",
    on_complete: Callable[[dict], None] | None = None
) -> Iterator[str]:
    assembled: Dict[str, Any] = {
        "assignmentInstructionsHtml": None,
        "stepByStepPlanHtml": None,
        "promptsHtml": None,
        "supportTools": {
            "toolsHtml": None,
            "aiPromptingHtml": None,
            "aiPolicyHtml": None,
        },
        "motivationalMessageHtml": None,
    }
    buffers: Dict[str, str] = {}

    def _emit_section(key: str, html: str):
        # Map nested keys like supportTools.toolsHtml
        if key.startswith("supportTools."):
            _, sub = key.split(".", 1)
            if sub not in ("toolsHtml", "aiPromptingHtml", "aiPolicyHtml"):
                return  # ignore unknown subkeys
            assembled["supportTools"][sub] = html
        elif key.startswith("template."):
            # Disallow legacy template.* sections in streaming path
            return
        elif key in assembled:
            assembled[key] = html
        else:
            # Ignore unknown keys but surface for debugging
            pass
        # Stream the finished section to client
        yield f'event: section\ndata: {json.dumps({"key": key, "html": html})}\n\n'

    try:
        with client.responses.stream(
            model=model,
            input=messages,
            tools=EMIT_SECTION_TOOL,
            tool_choice="auto",
            temperature=0.2,
            max_output_tokens=9000
        ) as stream:
            for event in stream:
                et = event.type

                # Ignore any plain text; we only want tool calls
                if et == "response.output_text.delta":
                    continue

                # --- Function-call style ---
                if et == "response.function_call_arguments.delta":
                    k = _buf_key(event)
                    if k:
                        buffers.setdefault(k, "")
                        if event.delta:
                            buffers[k] += event.delta
                    continue

                if et == "response.function_call_arguments.done":
                    k = _buf_key(event)
                    raw = buffers.pop(k, "")
                    payload = _parse_args(raw)
                    key = payload.get("key")
                    html = payload.get("html") or payload.get("value")
                    if key and isinstance(html, str):
                        for frame in _emit_section(key, html):
                            yield frame
                    else:
                        yield f'event: debug\ndata: {json.dumps({"unexpected_payload": payload})}\n\n'
                    continue

                # --- Responses-tool style ---
                if et == "response.tool_call.delta":
                    k = _buf_key(event)
                    if k:
                        buffers.setdefault(k, "")
                        if event.delta:
                            buffers[k] += event.delta
                    continue

                if et == "response.tool_call.completed":
                    k = _buf_key(event)
                    raw = buffers.pop(k, "")
                    payload = _parse_args(raw)
                    key = payload.get("key")
                    html = payload.get("html") or payload.get("value")
                    if key and isinstance(html, str):
                        for frame in _emit_section(key, html):
                            yield frame
                    else:
                        yield f'event: debug\ndata: {json.dumps({"unexpected_payload": payload})}\n\n'
                    continue

                if et == "response.completed":
                    # Prune Nones
                    final_obj = {
                        "assignmentInstructionsHtml": assembled["assignmentInstructionsHtml"],
                        "stepByStepPlanHtml": assembled["stepByStepPlanHtml"],
                        "promptsHtml": assembled["promptsHtml"],
                        "supportTools": {
                            "toolsHtml": assembled["supportTools"]["toolsHtml"],
                            "aiPromptingHtml": assembled["supportTools"]["aiPromptingHtml"],
                            "aiPolicyHtml": assembled["supportTools"]["aiPolicyHtml"],
                        },
                        "motivationalMessageHtml": assembled["motivationalMessageHtml"],
                    }
                    # Optional: validate before persisting (see validator below)
                    if on_complete:
                        on_complete(final_obj)
                    yield f'event: complete\ndata: {json.dumps({"object": final_obj})}\n\n'

                if et == "response.error":
                    yield f'event: error\ndata: {json.dumps({"message": event.error.get("message", "Unknown error")})}\n\n'
                    break

    except Exception as e:
        yield f'event: error\ndata: {json.dumps({"message": str(e)})}\n\n'
