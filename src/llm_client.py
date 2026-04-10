"""LLM API client with retries and error handling."""

from __future__ import annotations

import logging
import time
from typing import Any

import anthropic

from .config import Config

logger = logging.getLogger(__name__)


class LLMClient:
    """Wrapper around the Anthropic API with retry logic."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.client = anthropic.Anthropic(api_key=config.api_key)

    def call(self, prompt: str) -> str:
        """Send prompt to LLM and return raw text response.

        Retries on transient errors with exponential backoff.
        """
        last_error: Exception | None = None

        for attempt in range(1, self.config.max_retries + 1):
            try:
                logger.info("LLM call attempt %d/%d", attempt, self.config.max_retries)
                message = self.client.messages.create(
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = _extract_text(message)
                logger.info("LLM response received (%d chars)", len(text))
                return text

            except anthropic.RateLimitError as e:
                last_error = e
                delay = self.config.retry_base_delay * (2 ** (attempt - 1))
                logger.warning("Rate limited, retrying in %.1fs ...", delay)
                time.sleep(delay)

            except anthropic.APITimeoutError as e:
                last_error = e
                delay = self.config.retry_base_delay * (2 ** (attempt - 1))
                logger.warning("API timeout, retrying in %.1fs ...", delay)
                time.sleep(delay)

            except anthropic.APIConnectionError as e:
                last_error = e
                delay = self.config.retry_base_delay * (2 ** (attempt - 1))
                logger.warning("Connection error, retrying in %.1fs ...", delay)
                time.sleep(delay)

            except anthropic.APIStatusError as e:
                # 5xx errors are retryable; 4xx (except 429) are not
                if e.status_code >= 500:
                    last_error = e
                    delay = self.config.retry_base_delay * (2 ** (attempt - 1))
                    logger.warning("Server error %d, retrying in %.1fs ...", e.status_code, delay)
                    time.sleep(delay)
                else:
                    raise

        raise RuntimeError(f"LLM call failed after {self.config.max_retries} attempts: {last_error}")


def _extract_text(message: Any) -> str:
    """Extract text content from Anthropic message response."""
    parts = []
    for block in message.content:
        if block.type == "text":
            parts.append(block.text)
    return "\n".join(parts)
