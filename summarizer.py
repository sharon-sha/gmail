from openai import OpenAI

from config import Settings
from gmail_client import EmailMessage

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class EmailSummarizer:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.groq_api_key,
            base_url=GROQ_BASE_URL,
        )

    def summarize(self, email: EmailMessage) -> str:
        prompt = f"Summarize this email:\n{email.subject}\n\n{email.snippet}"

        response = self._client.chat.completions.create(
            model=self._settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Groq returned an empty summary")

        return content.strip()
