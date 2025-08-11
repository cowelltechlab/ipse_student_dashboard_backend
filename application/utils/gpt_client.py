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
    model: str = "gpt-4o-2024-08-06",
    on_complete: Callable[[dict], None] | None = None
) -> Iterator[str]:
    assembled: Dict[str, Any] = {
        "assignmentInstructionsHtml": None,
        "stepByStepPlanHtml": None,
        "myPlanChecklistHtml": None,
        "motivationalMessageHtml": None,
    }
    buffers: Dict[str, str] = {}

    try:
        with client.responses.stream(
            model=model,
            input=messages,
            tools=EMIT_SECTION_TOOL,
            tool_choice="auto",
            temperature=0.2,       # more deterministic tool behavior
            max_output_tokens=9000
        ) as stream:
            for event in stream:
                et = event.type

                # We explicitly forbid plain text in the system header; ignore if any leaks
                if et == "response.output_text.delta":
                    continue

                # ----- Chat-Completions style function-calls -----
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
                    if not raw:
                        yield 'event: error\ndata: {"message":"empty tool args"}\n\n'
                        continue

                    payload = _parse_args(raw)
                    key = payload.get("key")
                    html = payload.get("html") or payload.get("value")

                    if key and isinstance(html, str):
                        # assemble nested objects if needed
                        if key.startswith("template."):
                            assembled.setdefault("template", {})
                            assembled["template"][key.split(".", 1)[1]] = html
                        elif key.startswith("supportTools."):
                            assembled.setdefault("supportTools", {})
                            assembled["supportTools"][key.split(".", 1)[1]] = html
                        else:
                            assembled[key] = html

                        # stream the finished section
                        yield f'event: section\ndata: {json.dumps({"key": key, "html": html})}\n\n'
                    else:
                        # surface unexpected payload
                        yield f'event: debug\ndata: {json.dumps({"unexpected_payload": payload})}\n\n'
                    continue

                # ----- Responses-style tool events (future-proof) -----
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
                    if not raw:
                        continue

                    payload = _parse_args(raw)
                    key = payload.get("key")
                    html = payload.get("html") or payload.get("value")

                    if key and isinstance(html, str):
                        if key.startswith("template."):
                            assembled.setdefault("template", {})
                            assembled["template"][key.split(".", 1)[1]] = html
                        elif key.startswith("supportTools."):
                            assembled.setdefault("supportTools", {})
                            assembled["supportTools"][key.split(".", 1)[1]] = html
                        else:
                            assembled[key] = html

                        yield f'event: section\ndata: {json.dumps({"key": key, "html": html})}\n\n'
                    else:
                        yield f'event: debug\ndata: {json.dumps({"unexpected_payload": payload})}\n\n'
                    continue

                # ----- End of response -----
                if et == "response.completed":
                    final_obj = {k: v for k, v in assembled.items() if v not in (None, {})}
                    if on_complete:
                        on_complete(final_obj)
                    yield f'event: complete\ndata: {json.dumps({"object": final_obj})}\n\n'

                if et == "response.error":
                    yield f'event: error\ndata: {json.dumps({"message": event.error.get("message","Unknown error")})}\n\n'
                    break

    except Exception as e:
        yield f'event: error\ndata: {json.dumps({"message": str(e)})}\n\n'
