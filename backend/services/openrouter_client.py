from __future__ import annotations

from typing import Any
import json

import httpx

from utils.config import settings


class OpenRouterClient:
    def __init__(self) -> None:
        # Allow existing AGENT_THREE_API_KEY setups to keep working after the provider switch.
        self.api_key = (settings.openrouter_api_key or settings.agent_three_api_key or "").strip()
        self.base_url = settings.openrouter_base_url.rstrip("/")

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
            raise RuntimeError("OpenRouter API key is not configured.")

        response = self._post(
            "/chat/completions",
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        body: dict[str, Any] = response.json()
        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("OpenRouter returned an unexpected response shape.") from exc

    def embeddings(self, texts: list[str], model: str) -> list[list[float]]:
        if not self.enabled:
            raise RuntimeError("OpenRouter API key is not configured.")

        response = self._post("/embeddings", {"model": model, "input": texts})
        body: dict[str, Any] = response.json()
        return [item["embedding"] for item in body["data"]]

    def _post(self, path: str, payload: dict[str, Any]) -> httpx.Response:
        try:
            response = httpx.post(
                f"{self.base_url}{path}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            detail = self._extract_error_detail(exc.response.text).lower()
            if exc.response.status_code in {401, 403}:
                raise RuntimeError("OpenRouter authentication failed.") from exc
            if exc.response.status_code == 429 or "limit" in detail or "quota" in detail:
                raise RuntimeError("API call limit reached, change the api key.") from exc
            raise RuntimeError(f"OpenRouter request failed: {exc.response.status_code} {exc.response.text}") from exc

    def _extract_error_detail(self, response_text: str) -> str:
        try:
            payload = json.loads(response_text)
        except json.JSONDecodeError:
            return response_text

        error = payload.get("error")
        if isinstance(error, dict):
            return " ".join(str(error.get(key, "")) for key in ("type", "code", "message")).strip()
        return response_text
