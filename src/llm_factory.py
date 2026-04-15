"""LLM provider factory.

Selects the correct client based on config.llm_provider.
Supported: "yandex" (Yandex GPT), "anthropic" (Claude).
"""

from __future__ import annotations

from typing import Protocol

from .config import Config


class LLMProtocol(Protocol):
    def call(self, prompt: str) -> str: ...


def build_llm_client(config: Config) -> LLMProtocol:
    provider = config.llm_provider.lower()

    if provider == "yandex":
        from .yandex_client import YandexGPTClient
        return YandexGPTClient(config)

    if provider == "anthropic":
        from .llm_client import LLMClient
        return LLMClient(config)

    raise ValueError(
        f"Unknown LLM provider: {provider}. Supported: yandex, anthropic"
    )
