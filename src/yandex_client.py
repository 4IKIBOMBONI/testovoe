"""Yandex GPT API client (Yandex Cloud AI Studio / Foundation Models).

Docs: https://yandex.cloud/ru/docs/foundation-models/operations/yandexgpt/create-prompt
Endpoint: https://llm.api.cloud.yandex.net/foundationModels/v1/completion
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request

from .config import Config

logger = logging.getLogger(__name__)

YANDEX_ENDPOINT = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


class YandexGPTClient:
    """Minimal Yandex GPT client using urllib (no extra deps)."""

    def __init__(self, config: Config) -> None:
        self.config = config
        if not config.api_key:
            raise ValueError(
                "YANDEX_API_KEY not set. Create an API key in Yandex Cloud AI Studio "
                "and export it: export YANDEX_API_KEY=AQVN..."
            )
        if not config.yandex_folder_id:
            raise ValueError(
                "YANDEX_FOLDER_ID not set. Find it in Yandex Cloud console "
                "(the b1... id next to your folder) and export it: "
                "export YANDEX_FOLDER_ID=b1..."
            )

    def _build_model_uri(self) -> str:
        """Yandex GPT uses URIs like gpt://<folder_id>/yandexgpt/latest."""
        model = self.config.model
        if model.startswith("gpt://"):
            return model
        # Accept either "yandexgpt/latest" or just "yandexgpt"
        if "/" not in model:
            model = f"{model}/latest"
        return f"gpt://{self.config.yandex_folder_id}/{model}"

    def call(self, prompt: str) -> str:
        """Send prompt to Yandex GPT and return text response."""
        body = {
            "modelUri": self._build_model_uri(),
            "completionOptions": {
                "stream": False,
                "temperature": self.config.temperature,
                "maxTokens": str(self.config.max_tokens),
            },
            "messages": [
                {"role": "user", "text": prompt},
            ],
        }
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")

        headers = {
            "Authorization": f"Api-Key {self.config.api_key}",
            "Content-Type": "application/json",
            "x-folder-id": self.config.yandex_folder_id,
        }

        last_error: Exception | None = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                logger.info("Yandex GPT call attempt %d/%d", attempt, self.config.max_retries)
                req = urllib.request.Request(
                    YANDEX_ENDPOINT, data=data, headers=headers, method="POST"
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))

                text = _extract_text(payload)
                logger.info("Yandex GPT response received (%d chars)", len(text))
                return text

            except urllib.error.HTTPError as e:
                body_txt = e.read().decode("utf-8", errors="replace")
                last_error = RuntimeError(f"HTTP {e.code}: {body_txt}")
                # Retry on 5xx and 429
                if e.code >= 500 or e.code == 429:
                    delay = self.config.retry_base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "Yandex GPT HTTP %d, retrying in %.1fs ...", e.code, delay
                    )
                    time.sleep(delay)
                else:
                    raise last_error

            except urllib.error.URLError as e:
                last_error = e
                delay = self.config.retry_base_delay * (2 ** (attempt - 1))
                logger.warning("Yandex GPT network error, retrying in %.1fs ...", delay)
                time.sleep(delay)

            except TimeoutError as e:
                last_error = e
                delay = self.config.retry_base_delay * (2 ** (attempt - 1))
                logger.warning("Yandex GPT timeout, retrying in %.1fs ...", delay)
                time.sleep(delay)

        raise RuntimeError(
            f"Yandex GPT call failed after {self.config.max_retries} attempts: {last_error}"
        )


def _extract_text(payload: dict) -> str:
    """Extract generated text from Yandex GPT response payload."""
    try:
        alternatives = payload["result"]["alternatives"]
        if not alternatives:
            raise ValueError("empty alternatives")
        return alternatives[0]["message"]["text"]
    except (KeyError, TypeError, ValueError) as e:
        raise RuntimeError(
            f"Unexpected Yandex GPT response structure: {e}. Payload: {payload}"
        )
