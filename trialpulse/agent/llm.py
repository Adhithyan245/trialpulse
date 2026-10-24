"""The LLM boundary for the report agent.

A :class:`JSONModel` turns a system prompt and a user prompt into a validated
pydantic instance. :class:`GeminiModel` is the real implementation backed by the
google-genai SDK; tests inject a fake model instead of calling the network.
"""

from __future__ import annotations

import os
import time
from typing import Protocol, runtime_checkable

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError


class LLMError(RuntimeError):
    """Raised when the model cannot produce a valid structured response."""


@runtime_checkable
class JSONModel(Protocol):
    name: str

    def generate(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        ...


# Retry back-off, in seconds, for retryable API errors (429 / 5xx). Two retries
# per model only, then move on to the next model.
_BACKOFF = (2, 4)


def _parse_models(models: list[str] | None) -> list[str]:
    """Resolve the ordered model list from the constructor arg or the env.

    The primary comes from GEMINI_MODEL; optional comma-separated fallbacks come
    from GEMINI_FALLBACK_MODELS. A ``models`` argument overrides the env.
    """
    if models is not None:
        resolved = [m.strip() for m in models if m and m.strip()]
    else:
        primary = os.environ.get("GEMINI_MODEL")
        if not primary or not primary.strip():
            raise LLMError("GEMINI_MODEL is not set")
        resolved = [primary.strip()]
        raw_fallbacks = os.environ.get("GEMINI_FALLBACK_MODELS", "")
        resolved.extend(m.strip() for m in raw_fallbacks.split(",") if m.strip())
    if not resolved:
        raise LLMError("no Gemini models configured")
    return resolved


class GeminiModel:
    """Google Gemini implementation of :class:`JSONModel`.

    Tries each configured model in order. For a single model it retries 429/5xx
    errors with back-off (2 s then 4 s), then moves on to the next model.
    Non-retryable client errors (4xx other than 429) move straight to the next
    model without sleeping. :class:`LLMError` is raised only when every model has
    failed; its message lists each model and its last error code.
    """

    def __init__(
        self,
        api_key: str | None = None,
        models: list[str] | None = None,
        sleep=time.sleep,
    ) -> None:
        load_dotenv()
        key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY")
        if not key:
            raise LLMError("GEMINI_API_KEY is not set")

        self._api_key = key
        self._models = _parse_models(models)
        # ``name`` reports the model behind the most recent successful response;
        # before any call it is the primary.
        self.name = self._models[0]
        self._sleep = sleep
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai
            from google.genai import types

            self._client = genai.Client(
                api_key=self._api_key,
                http_options=types.HttpOptions(
                    timeout=45000,
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            )
        return self._client

    def generate(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        from google.genai import errors, types

        client = self._get_client()
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=schema,
        )

        last_errors: list[tuple[str, object]] = []

        for model_name in self._models:
            try:
                result = self._generate_one(client, model_name, user, config, errors, schema)
            except _ModelFailed as failed:
                last_errors.append((model_name, failed.code))
                continue
            self.name = model_name
            return result

        detail = ", ".join(f"{m} (code {c})" for m, c in last_errors)
        raise LLMError(f"all Gemini models failed: {detail}")

    def _generate_one(self, client, model_name, user, config, errors, schema):
        """Try a single model: retry 429/5xx with back-off, one invalid-JSON
        retry. Raise :class:`_ModelFailed` to move on to the next model."""
        import httpx

        json_retry_used = False
        attempt = 0
        while True:
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=user,
                    config=config,
                )
            except httpx.TransportError:
                # Network errors (RemoteProtocolError, ConnectError, ReadTimeout, etc.)
                # are retryable like 5xx errors.
                if attempt < len(_BACKOFF):
                    self._sleep(_BACKOFF[attempt])
                    attempt += 1
                    continue
                raise _ModelFailed("network") from None
            except errors.APIError as exc:
                code = getattr(exc, "code", None)
                if code == 429 or (isinstance(code, int) and code >= 500):
                    if attempt < len(_BACKOFF):
                        self._sleep(_BACKOFF[attempt])
                        attempt += 1
                        continue
                    raise _ModelFailed(code) from exc
                # Non-retryable client error (4xx other than 429): next model.
                raise _ModelFailed(code) from exc

            parsed = getattr(resp, "parsed", None)
            if isinstance(parsed, schema):
                return parsed
            try:
                return schema.model_validate_json(resp.text)
            except (ValidationError, ValueError) as exc:
                if not json_retry_used:
                    json_retry_used = True
                    continue
                raise LLMError("Gemini returned invalid JSON") from exc


class _ModelFailed(Exception):
    """Internal signal that a single model has exhausted its retries."""

    def __init__(self, code) -> None:
        super().__init__(str(code))
        self.code = code
