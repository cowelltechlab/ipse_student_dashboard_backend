import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_gpt_response(prompt: str, model: str = "gpt-3.5-turbo") -> str:
    if not client.api_key:
        raise RuntimeError("OpenAI API key not configured")

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()
