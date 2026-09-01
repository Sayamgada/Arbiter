import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


class LLMService:
    """
    Groq-backed language service.

    The LLM handles natural-language reasoning and generation.
    It does NOT authorize discounts, budgets, or transactions.
    """

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        model = os.getenv(
            "GROQ_MODEL",
            "openai/gpt-oss-120b",
        )

        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY must be configured"
            )

        self.model = model
        self.client = Groq(api_key=api_key)

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        )

        content = response.choices[0].message.content

        if not content:
            raise RuntimeError(
                "LLM returned an empty response"
            )

        return content.strip()