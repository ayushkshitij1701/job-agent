import json
import time
from typing import Protocol

RETRIES = 3
RETRY_STATUSES = {429, 500, 502, 503}


class LLM(Protocol):
    def ask_json(self, *, system: str, user: str, schema: dict) -> dict: ...


class RestLLM:
    """Shared plumbing for any HTTP JSON model API: POST with retries, then parse the JSON the model wrote.

    Subclasses define only the provider's wire format via build_request() and extract_text().
    """

    name = ""

    def __init__(self, session):
        self.session = session

    @classmethod
    def from_config(cls, cfg: dict, session) -> "RestLLM":
        raise NotImplementedError

    def build_request(self, system: str, user: str, schema: dict) -> tuple[str, dict, dict | None]:
        """Return (url, json body, headers)."""
        raise NotImplementedError

    def extract_text(self, data: dict) -> str:
        """Pull the model's text (a JSON document) out of the provider's response."""
        raise NotImplementedError

    def ask_json(self, *, system: str, user: str, schema: dict) -> dict:
        url, body, headers = self.build_request(system, user, schema)
        return json.loads(self.extract_text(self._post(url, body, headers)))

    def _post(self, url: str, body: dict, headers: dict | None) -> dict:
        for attempt in range(RETRIES + 1):
            resp = self.session.post(url, json=body, headers=headers, timeout=180)
            if resp.status_code in RETRY_STATUSES and attempt < RETRIES:
                time.sleep(float(resp.headers.get("Retry-After", 2 ** attempt * 2)))
                continue
            resp.raise_for_status()
            return resp.json()
        raise AssertionError("unreachable")
