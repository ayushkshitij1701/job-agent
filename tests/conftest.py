import json
from pathlib import Path

import pytest
import requests

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture():
    def _load(name: str) -> dict:
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    return _load


class StubResponse:
    def __init__(self, payload: dict, status: int = 200, headers: dict | None = None):
        self._payload = payload
        self.status_code = status
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")

    def json(self):
        return self._payload


class StubSession:
    """Serves queued responses in order; records every call so tests can check pagination and bodies."""

    def __init__(self, responses: list):
        self._responses = [r if isinstance(r, StubResponse) else StubResponse(r) for r in responses]
        self.calls: list[dict] = []

    def _next(self, method, url, kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        return self._responses.pop(0)

    def get(self, url, **kwargs):
        return self._next("GET", url, kwargs)

    def post(self, url, **kwargs):
        return self._next("POST", url, kwargs)


@pytest.fixture
def stub_session():
    return StubSession
