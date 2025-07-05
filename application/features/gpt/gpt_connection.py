import os
import openai

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

def get_gpt_response(prompt: str, model: str = "gpt-3.5-turbo") -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OpenAI API key not configured")

    response = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()
