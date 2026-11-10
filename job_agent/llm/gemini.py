"""Google Gemini API, REST. POST .../v1beta/models/{model}:generateContent with a response schema."""
import os

from .base import RestLLM

BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _gemini_schema(schema: dict):
    """Gemini's responseSchema is an OpenAPI subset and rejects `additionalProperties`; drop it recursively."""
    if isinstance(schema, dict):
        return {k: _gemini_schema(v) for k, v in schema.items() if k != "additionalProperties"}
    if isinstance(schema, list):
        return [_gemini_schema(v) for v in schema]
    return schema


class GeminiLLM(RestLLM):
    name = "gemini"

    def __init__(self, model: str, api_key: str, session):
        super().__init__(session)
        self.model, self.api_key = model, api_key

    @classmethod
    def from_config(cls, cfg: dict, session) -> "GeminiLLM":
        return cls(model=cfg["model"], api_key=os.environ["GEMINI_API_KEY"], session=session)

    def build_request(self, system, user, schema):
        body = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": _gemini_schema(schema)},
        }
        return f"{BASE}/{self.model}:generateContent", body, {"x-goog-api-key": self.api_key}

    def extract_text(self, data):
        return data["candidates"][0]["content"]["parts"][0]["text"]
