from openai import OpenAI

from app.config import get_app_settings
from gmail_client import EmailMessage

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def summarize_email(email: EmailMessage) -> str:
    settings = get_app_settings()
    client = OpenAI(api_key=settings.groq_api_key, base_url=GROQ_BASE_URL)
    prompt = f"Summarize this email:\n{email.subject}\n\n{email.snippet}"

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "user", "content": prompt}],
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Groq returned an empty summary")
    return content.strip()
