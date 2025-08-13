from typing import Optional
import tiktoken
from openai import OpenAI

client = OpenAI()

def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    Counts how many tokens a text will consume for the specified model.
    """
    # Map new/unknown models to a known encoding
    if model.startswith("gpt-4.1"):
        enc = tiktoken.get_encoding("cl100k_base")
    else:
        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))



def get_gpt_response(
    prompt: str,
    model: str = "gpt-3.5-turbo",
    override_max_tokens: Optional[int] = None
) -> str:
    if not client.api_key:
        raise RuntimeError("OpenAI API key not configured")

    # --- Count tokens in the prompt ---
    prompt_tokens = count_tokens(prompt, model=model)
    print(f"Prompt token count: {prompt_tokens}")

    # --- Set safe limits ---
    context_limit = 4096 if "3.5" in model else 128000  # adjust for gpt-4.1
    default_max_output_tokens = 500  # keep the original default
    max_output_tokens = override_max_tokens or default_max_output_tokens

    # --- Validate against context window ---
    if prompt_tokens + max_output_tokens > context_limit:
        raise ValueError(
            f"Prompt ({prompt_tokens} tokens) is too large for {model}'s {context_limit}-token limit. "
            "Consider splitting the input or lowering override_max_tokens."
        )

    # --- Make the API call ---
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_output_tokens,
        temperature=0.7,
    )

    return resp.choices[0].message.content.strip()
