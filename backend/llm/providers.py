from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from backend.config import settings

log = logging.getLogger(__name__)
SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMProviderError(RuntimeError):
    """A provider failed after its bounded retry policy was exhausted."""


class LLMAuthenticationError(LLMProviderError):
    pass


class LLMRateLimitError(LLMProviderError):
    pass


@dataclass(frozen=True)
class LLMResponse:
    data: Any
    provider: str
    model: str
    fallback_from: str | None = None
    attempts: int = 1
    cached: bool = False

    def metadata(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "provider": self.provider,
            "model": self.model,
            "attempts": self.attempts,
            "cached": self.cached,
        }
        if self.fallback_from:
            result["fallback_from"] = self.fallback_from
        return result


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in content)
    return str(content)


def _parse_json(content: Any) -> Any:
    raw = _content_text(content).strip()
    if raw.startswith("```"):
        raw = raw.strip("`").removeprefix("json").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                pass
        raise LLMProviderError(f"Provider returned invalid JSON: {exc}") from exc


def _classify_error(exc: Exception) -> type[LLMProviderError]:
    text = str(exc).lower()
    status = str(getattr(exc, "status_code", ""))
    if status == "401" or any(token in text for token in ("unauthorized", "invalid api key", "authentication", "api_key")):
        return LLMAuthenticationError
    if status == "429" or any(token in text for token in ("rate limit", "ratelimit", "too many requests", "throttl")):
        return LLMRateLimitError
    return LLMProviderError


def _provider_model(provider: str, model: str | None, temperature: float) -> Any:
    normalized = provider.lower().strip()
    selected_model = model or (settings.groq_model if normalized == "groq" else settings.ollama_model)
    if normalized == "groq":
        if not settings.groq_api_key:
            raise LLMAuthenticationError("GROQ_API_KEY is not configured while LLM_PROVIDER=groq.")
        try:
            from langchain_groq import ChatGroq
        except ImportError as exc:
            raise LLMProviderError("langchain-groq is missing. Install it with: pip install langchain-groq") from exc
        return ChatGroq(
            model=selected_model,
            api_key=settings.groq_api_key,
            temperature=temperature,
            timeout=settings.groq_timeout,
            max_retries=0,
            reasoning_effort=settings.groq_reasoning_effort,
        )
    if normalized == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError as exc:
            raise LLMProviderError("langchain-ollama is missing. Install it with: pip install langchain-ollama") from exc
        return ChatOllama(
            model=selected_model,
            base_url=settings.ollama_url,
            temperature=temperature,
            format="json",
        )
    raise LLMProviderError(f"Unsupported LLM provider {provider!r}. Use groq or ollama.")


def _cache_file(cache_payload: dict[str, Any], schema: type[BaseModel] | None) -> Path:
    payload = {"schema": schema.__name__ if schema else "json", "payload": cache_payload}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return settings.llm_cache_dir / f"{digest}.json"


def _validate(data: Any, schema: type[SchemaT] | None) -> Any:
    if schema is None:
        return data
    return schema.model_validate(data)


def _invoke_one(provider: str, messages: list[Any], schema: type[SchemaT] | None, temperature: float, model_name: str | None = None) -> tuple[Any, int]:
    model = _provider_model(provider, model_name, temperature)
    attempts = 0
    last_error: Exception | None = None
    for attempt in range(settings.llm_max_retries + 1):
        attempts += 1
        try:
            if schema is not None:
                try:
                    method = "json_schema" if provider == "groq" else "json_mode"
                    structured = model.with_structured_output(schema, method=method)
                    value = structured.invoke(messages)
                    return _validate(value.model_dump(mode="json") if isinstance(value, BaseModel) else value, schema), attempts
                except Exception as structured_error:
                    structured_error_type = _classify_error(structured_error)
                    if structured_error_type in {LLMAuthenticationError, LLMRateLimitError}:
                        raise structured_error
                    log.debug("Structured output unavailable for %s; retrying in JSON mode: %s", provider, structured_error)
            response = model.invoke(messages)
            return _validate(_parse_json(response.content), schema), attempts
        except Exception as exc:
            last_error = exc
            error_type = _classify_error(exc)
            if error_type is LLMAuthenticationError:
                raise error_type(f"{provider} authentication failed: {exc}") from exc
            if attempt >= settings.llm_max_retries:
                raise error_type(f"{provider} failed after {attempts} attempt(s): {exc}") from exc
            log.warning("%s LLM attempt %d/%d failed; retrying: %s", provider, attempt + 1, settings.llm_max_retries + 1, exc)
    raise LLMProviderError(f"{provider} failed: {last_error}")


def invoke_json(
    messages: list[Any],
    *,
    schema: type[SchemaT] | None = None,
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.1,
    cache_payload: dict[str, Any] | None = None,
) -> LLMResponse:
    """Invoke the configured provider with bounded retries and explicit fallback.

    The response never contains credentials. A fallback is recorded both in the
    returned metadata and in the warning log so provider changes are observable.
    """

    primary = (provider or settings.llm_provider).lower().strip()
    fallback = settings.llm_fallback_provider.lower().strip() if settings.llm_fallback_provider else ""
    cache_context = dict(cache_payload or {})
    cache_context.update({
        "provider": primary,
        "fallback_provider": fallback,
        "groq_model": settings.groq_model,
        "ollama_model": settings.ollama_model,
        "groq_reasoning_effort": settings.groq_reasoning_effort,
        "requested_model": model or "",
        "temperature": temperature,
        "schema_version": cache_context.get("schema_version", "1"),
    })
    cache_file = _cache_file(cache_context, schema) if cache_payload and settings.llm_cache_enabled else None
    if cache_file and cache_file.exists():
        try:
            cached_blob = json.loads(cache_file.read_text(encoding="utf-8"))
            cached_data = cached_blob.get("data", cached_blob)
            cached = _validate(cached_data, schema)
            cached_provider = str(cached_blob.get("provider", primary))
            cached_model = str(cached_blob.get("model", settings.groq_model if cached_provider == "groq" else settings.ollama_model))
            cached_fallback = cached_blob.get("fallback_from")
            log.info("LLM planning cache hit provider=%s model=%s", cached_provider, cached_model)
            return LLMResponse(cached, cached_provider, cached_model, fallback_from=cached_fallback, cached=True)
        except Exception as exc:
            log.warning("Ignoring invalid LLM planning cache %s: %s", cache_file, exc)

    providers = [primary]
    if fallback and fallback != primary:
        providers.append(fallback)
    failures: list[str] = []
    for selected in providers:
        try:
            selected_model = model if selected == primary else None
            data, attempts = _invoke_one(selected, messages, schema, temperature, selected_model)
            resolved_model = selected_model or (settings.groq_model if selected == "groq" else settings.ollama_model)
            fallback_from = primary if selected != primary else None
            if fallback_from:
                log.warning("LLM provider fallback selected: %s -> %s", fallback_from, selected)
            response = LLMResponse(data, selected, resolved_model, fallback_from=fallback_from, attempts=attempts)
            if cache_file:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(json.dumps({
                    "data": data.model_dump(mode="json") if isinstance(data, BaseModel) else data,
                    "provider": selected,
                    "model": resolved_model,
                    "fallback_from": fallback_from,
                }, indent=2), encoding="utf-8")
            log.info("LLM planning provider=%s model=%s attempts=%d%s", selected, resolved_model, attempts, f" fallback_from={primary}" if fallback_from else "")
            return response
        except LLMAuthenticationError as exc:
            failures.append(str(exc))
            if selected == primary and fallback:
                log.warning("Primary LLM authentication failed; trying configured fallback provider %s.", fallback)
                continue
            break
        except LLMProviderError as exc:
            failures.append(str(exc))
            if selected == primary and fallback:
                log.warning("Primary LLM provider failed; trying configured fallback provider %s.", fallback)
                continue
            break
    raise LLMProviderError("No configured LLM provider succeeded: " + " | ".join(failures))
