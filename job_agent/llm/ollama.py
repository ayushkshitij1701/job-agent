"""Local Ollama server. POST {url}/api/chat with `format` set to the JSON schema (Ollama >= 0.5)."""
from .base import RestLLM

DEFAULT_URL = "http://localhost:11434"
NUM_CTX = 16384       # resume + JD + rules is ~4-6K tokens; the tailored resume comes back in the same window


class OllamaLLM(RestLLM):
    name = "ollama"

    def __init__(self, model: str, url: str, session, think: bool = False):
        super().__init__(session)
        self.model, self.url, self.think = model, url.rstrip("/"), think

    @classmethod
    def from_config(cls, cfg: dict, session) -> "OllamaLLM":
        return cls(model=cfg["model"], url=cfg.get("url", DEFAULT_URL), session=session,
                   think=bool(cfg.get("think", False)))

    def build_request(self, system, user, schema):
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "format": schema,
            "stream": False,
            "think": self.think,  # thinking models (qwen3.5, gemma4) reason for ~1.5K tokens first; off = 4s vs 54s a call
            "options": {"num_ctx": NUM_CTX, "temperature": 0},
        }
        return f"{self.url}/api/chat", body, None

    def extract_text(self, data):
        return data["message"]["content"]
