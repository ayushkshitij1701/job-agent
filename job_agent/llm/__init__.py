"""LLM providers. The rest of the agent only ever calls `client.ask_json(system=, user=, schema=)`.

To add a provider: subclass RestLLM in a new module (request/response shape only) and register it here.
"""
from .base import LLM, RestLLM
from .gemini import GeminiLLM
from .ollama import OllamaLLM

PROVIDERS: dict[str, type[RestLLM]] = {GeminiLLM.name: GeminiLLM, OllamaLLM.name: OllamaLLM}


def make_client(llm_cfg: dict, session) -> LLM:
    provider = llm_cfg.get("provider")
    if provider not in PROVIDERS:
        raise ValueError(f"unknown llm.provider {provider!r}; known: {sorted(PROVIDERS)}")
    return PROVIDERS[provider].from_config(llm_cfg.get(provider, {}), session)
