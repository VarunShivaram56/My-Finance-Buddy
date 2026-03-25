from __future__ import annotations

import logging
import time
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class GroqClient:
    def __init__(self, api_key: str, *, agent_name: str = "agent") -> None:
        self.api_key = api_key.strip()
        self.agent_name = agent_name
        self.base_url = "https://api.groq.com/openai/v1"

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def chat_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        if not self.enabled:
            raise RuntimeError(f"{self.agent_name} API key is not configured.")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = self._post_with_retries("/chat/completions", payload)
        body: dict[str, Any] = response.json()
        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"{self.agent_name} returned an unexpected response shape.") from exc

    def _post_with_retries(self, path: str, payload: dict[str, Any], retries: int = 2) -> httpx.Response:
        last_error: Exception | None = None

        for attempt in range(retries + 1):
            started_at = time.perf_counter()
            try:
                response = httpx.post(
                    f"{self.base_url}{path}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=45,
                )
                response.raise_for_status()
                latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
                logger.info("%s chat_completion succeeded in %sms using model %s", self.agent_name, latency_ms, payload.get("model"))
                return response
            except httpx.TimeoutException as exc:
                latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
                last_error = RuntimeError(f"{self.agent_name} request timed out after {latency_ms}ms.")
                logger.warning("%s timeout on attempt %s/%s", self.agent_name, attempt + 1, retries + 1)
            except httpx.HTTPStatusError as exc:
                latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
                detail = exc.response.text.lower()
                logger.warning(
                    "%s HTTP error on attempt %s/%s after %sms: %s",
                    self.agent_name,
                    attempt + 1,
                    retries + 1,
                    latency_ms,
                    exc.response.text,
                )
                if exc.response.status_code in {401, 403}:
                    raise RuntimeError(f"{self.agent_name} authentication failed.") from exc
                if exc.response.status_code == 429 or "limit" in detail or "quota" in detail:
                    raise RuntimeError("API call limit reached, change the api key.") from exc
                last_error = RuntimeError(
                    f"{self.agent_name} request failed: {exc.response.status_code} {exc.response.text}"
                )
            except httpx.HTTPError as exc:
                logger.warning("%s transport error on attempt %s/%s: %s", self.agent_name, attempt + 1, retries + 1, exc)
                last_error = RuntimeError(f"{self.agent_name} request failed.")

            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))

        raise last_error or RuntimeError(f"{self.agent_name} request failed.")
