# import os
# from openai import OpenAI

# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# def get_gpt_response(prompt: str, model: str = "gpt-3.5-turbo") -> str:
#     if not client.api_key:
#         raise RuntimeError("OpenAI API key not configured")

#     resp = client.chat.completions.create(
#         model=model,
#         messages=[{"role": "user", "content": prompt}],
#         max_tokens=300,
#         temperature=0.7,
#     )
#     return resp.choices[0].message.content.strip()

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


def get_gpt_response(prompt: str, model: str = "gpt-3.5-turbo") -> str:
    if not client.api_key:
        raise RuntimeError("OpenAI API key not configured")

    # --- Count tokens in the prompt ---
    prompt_tokens = count_tokens(prompt, model=model)
    print(f"Prompt token count: {prompt_tokens}")

    # --- Set safe limits based on model context ---
    context_limit = 4096 if "3.5" in model else 128000  # adjust for other models
    max_output_tokens = 500

    # Check if input fits the model's context window
    if prompt_tokens + max_output_tokens > context_limit:
        raise ValueError(
            f"Prompt ({prompt_tokens} tokens) is too large for {model}'s {context_limit}-token limit. "
            "Consider using gpt-4.1 or splitting the input."
        )

    # --- Make the API call ---
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_output_tokens,
        temperature=0.7,
    )

    return resp.choices[0].message.content.strip()
