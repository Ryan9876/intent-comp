from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any, Protocol

from pydantic import ValidationError

from .errors import AuthorizationFailure, IntentCompilerError, ValidationFailure
from .llm_models import LLMAuditRecord, LLMPolicy, LLMRequest, LLMResponse, LLMUsage


class LLMAdapterError(IntentCompilerError):
    pass


class LLMBudgetExceeded(LLMAdapterError):
    pass


class LLMProvider(Protocol):
    name: str

    def generate(self, request: LLMRequest) -> LLMResponse: ...


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _extract_json(text: str) -> dict[str, Any] | list[Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
        if stripped.startswith("json"):
            stripped = stripped[4:].lstrip()
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValidationFailure("LLM response is not valid JSON") from exc
    if not isinstance(value, (dict, list)):
        raise ValidationFailure("Structured LLM response must be a JSON object or array")
    return value


class GovernedLLMClient:
    """Policy, budget, validation, and audit wrapper around an LLM provider."""

    def __init__(
        self,
        provider: LLMProvider,
        policy: LLMPolicy,
        audit_sink: Callable[[LLMAuditRecord], None] | None = None,
    ) -> None:
        self.provider = provider
        self.policy = policy
        self.audit_sink = audit_sink
        self.calls = 0
        self.input_chars = 0
        self.output_chars = 0
        self.estimated_cost_usd = 0.0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.usage_complete = True
        self.cost_complete = True

    def generate(self, request: LLMRequest) -> LLMResponse:
        self._validate_request(request)
        input_chars = len(request.system_instructions) + len(request.user_content)
        self._check_budget(input_chars=input_chars, output_chars=0, additional_calls=1)
        try:
            response = self.provider.generate(request)
        except Exception:
            record = LLMAuditRecord(
                request_id=request.request_id,
                provider=request.provider,
                model=request.model,
                purpose=request.purpose,
                data_classification=request.data_classification,
                request_sha256=_sha256(request.system_instructions + "\n" + request.user_content),
                prompt_content_recorded=self.policy.record_prompt_content,
                status="failed",
                input_chars=input_chars,
                output_chars=0,
            )
            self._audit(record)
            raise

        output_chars = len(response.text)
        self._check_budget(
            input_chars=input_chars,
            output_chars=output_chars,
            additional_calls=1,
            additional_cost=response.usage.estimated_cost_usd or 0.0,
        )
        if self.policy.require_structured_output and request.output_schema is not None:
            if response.parsed is None:
                response.parsed = _extract_json(response.text)
        self.calls += 1
        self.input_chars += input_chars
        self.output_chars += output_chars
        self.estimated_cost_usd += response.usage.estimated_cost_usd or 0.0
        if response.usage.input_tokens is None or response.usage.output_tokens is None:
            self.usage_complete = False
        else:
            self.input_tokens += response.usage.input_tokens
            self.output_tokens += response.usage.output_tokens
            self.total_tokens += response.usage.total_tokens or (response.usage.input_tokens + response.usage.output_tokens)
        if response.usage.estimated_cost_usd is None:
            self.cost_complete = False
        self._audit(
            LLMAuditRecord(
                request_id=request.request_id,
                response_id=response.response_id,
                provider=request.provider,
                model=request.model,
                purpose=request.purpose,
                data_classification=request.data_classification,
                request_sha256=response.request_sha256,
                output_sha256=response.output_sha256,
                prompt_content_recorded=self.policy.record_prompt_content,
                status=response.status,
                latency_ms=response.latency_ms,
                attempts=response.attempts,
                input_chars=input_chars,
                output_chars=output_chars,
                usage=response.usage,
            )
        )
        return response

    def _validate_request(self, request: LLMRequest) -> None:
        if request.provider != self.provider.name:
            raise AuthorizationFailure(
                f"Request provider {request.provider!r} does not match adapter {self.provider.name!r}"
            )
        if not self.policy.permits_model(request.provider, request.model):
            raise AuthorizationFailure(
                f"Provider/model is not allowed: {request.provider}/{request.model}"
            )
        if request.data_classification not in self.policy.permitted_data_classifications:
            raise AuthorizationFailure(
                f"Data classification is not permitted: {request.data_classification}"
            )
        if request.provider != "mock" and not self.policy.network_access:
            raise AuthorizationFailure("Network LLM access is disabled by policy")
        if self.policy.require_structured_output and request.output_schema is None:
            raise ValidationFailure("Policy requires a structured output schema")

    def _check_budget(
        self,
        input_chars: int,
        output_chars: int,
        additional_calls: int,
        additional_cost: float = 0.0,
    ) -> None:
        budget = self.policy.budget
        # The pre-call and post-call checks both use the current counter. The post-call
        # check verifies actual output before committing counters.
        if self.calls + additional_calls > budget.max_calls:
            raise LLMBudgetExceeded("LLM call budget exceeded")
        if self.input_chars + input_chars > budget.max_input_chars:
            raise LLMBudgetExceeded("LLM input character budget exceeded")
        if self.output_chars + output_chars > budget.max_output_chars:
            raise LLMBudgetExceeded("LLM output character budget exceeded")
        if (
            budget.max_estimated_cost_usd is not None
            and self.estimated_cost_usd + additional_cost > budget.max_estimated_cost_usd
        ):
            raise LLMBudgetExceeded("LLM estimated cost budget exceeded")

    def _audit(self, record: LLMAuditRecord) -> None:
        if self.audit_sink is not None:
            self.audit_sink(record)


class MockLLMAdapter:
    name = "mock"

    def __init__(
        self,
        responder: Callable[[LLMRequest], str | dict[str, Any] | list[Any]],
        model: str = "mock-governed-v1",
    ) -> None:
        self.responder = responder
        self.model = model

    def generate(self, request: LLMRequest) -> LLMResponse:
        started = time.perf_counter()
        value = self.responder(request)
        if isinstance(value, str):
            text = value
            parsed = None
        else:
            parsed = value
            text = json.dumps(value, ensure_ascii=False)
        request_hash = _sha256(request.system_instructions + "\n" + request.user_content)
        return LLMResponse(
            request_id=request.request_id,
            provider=self.name,
            model=request.model,
            status="completed",
            text=text,
            parsed=parsed,
            latency_ms=round((time.perf_counter() - started) * 1000, 3),
            request_sha256=request_hash,
            output_sha256=_sha256(text),
            raw_metadata={"adapter": "MockLLMAdapter"},
        )


class OpenAIResponsesAdapter:
    """Minimal standard-library adapter for the OpenAI Responses API.

    The adapter intentionally stores no API key and records no prompt content.
    Tests use a stub transport; live use requires OPENAI_API_KEY.
    """

    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str = "https://api.openai.com/v1/responses",
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
        transport: Callable[[urllib.request.Request, float], dict[str, Any]] | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.transport = transport or self._urlopen_transport

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise AuthorizationFailure("OPENAI_API_KEY is not configured")
        body: dict[str, Any] = {
            "model": request.model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": request.system_instructions}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": request.user_content}],
                },
            ],
            "max_output_tokens": request.max_output_tokens,
        }
        if request.output_schema is not None:
            body["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": request.output_schema_name,
                    "schema": request.output_schema,
                    "strict": True,
                }
            }
        payload = json.dumps(body).encode("utf-8")
        http_request = urllib.request.Request(
            self.endpoint,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        started = time.perf_counter()
        attempts = 0
        last_error: Exception | None = None
        while attempts <= self.max_retries:
            attempts += 1
            try:
                raw = self.transport(http_request, self.timeout_seconds)
                text, refusal = self._extract_text(raw)
                parsed = _extract_json(text) if request.output_schema is not None and text else None
                usage_raw = raw.get("usage") or {}
                usage = LLMUsage(
                    input_tokens=usage_raw.get("input_tokens"),
                    output_tokens=usage_raw.get("output_tokens"),
                    total_tokens=usage_raw.get("total_tokens"),
                )
                status = "refused" if refusal else "completed"
                return LLMResponse(
                    request_id=request.request_id,
                    provider=self.name,
                    model=request.model,
                    status=status,
                    text=text,
                    parsed=parsed,
                    refusal=refusal,
                    usage=usage,
                    latency_ms=round((time.perf_counter() - started) * 1000, 3),
                    attempts=attempts,
                    request_sha256=_sha256(request.system_instructions + "\n" + request.user_content),
                    output_sha256=_sha256(text) if text else None,
                    provider_response_id=raw.get("id"),
                    raw_metadata={"response_status": raw.get("status")},
                )
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code not in {408, 409, 429, 500, 502, 503, 504} or attempts > self.max_retries:
                    break
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                if attempts > self.max_retries:
                    break
            if attempts <= self.max_retries:
                time.sleep(min(0.25 * (2 ** (attempts - 1)), 2.0))
        raise LLMAdapterError(f"OpenAI request failed after {attempts} attempts: {last_error}")

    @staticmethod
    def _urlopen_transport(request: urllib.request.Request, timeout: float) -> dict[str, Any]:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _extract_text(raw: dict[str, Any]) -> tuple[str, str | None]:
        if isinstance(raw.get("output_text"), str):
            return raw["output_text"], None
        text_parts: list[str] = []
        refusal: str | None = None
        for item in raw.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    text_parts.append(content["text"])
                elif content.get("type") == "refusal":
                    refusal = content.get("refusal") or "Model refused the request"
        return "".join(text_parts), refusal
