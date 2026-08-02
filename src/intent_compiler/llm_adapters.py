from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any, Protocol

from .errors import AuthorizationFailure, IntentCompilerError, ValidationFailure
from .llm_models import LLMAuditRecord, LLMPolicy, LLMRequest, LLMResponse, LLMUsage
from .models import new_id


class LLMAdapterError(IntentCompilerError):
    pass


class LLMBudgetExceeded(LLMAdapterError):
    pass


class LLMStructuredOutputError(LLMAdapterError):
    """Raised after a provider response is recorded but cannot satisfy the schema contract."""

    def __init__(self, message: str, response: LLMResponse) -> None:
        super().__init__(message)
        self.response = response


class LLMProvider(Protocol):
    name: str

    def generate(self, request: LLMRequest) -> LLMResponse: ...


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _extract_json(text: str) -> dict[str, Any] | list[Any]:
    """Parse a complete object/array, tolerating fences or surrounding prose only.

    This intentionally does not invent closing braces or otherwise repair truncated JSON.
    """

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

    candidates = [stripped]
    candidates.extend(stripped[index:] for index, char in enumerate(stripped) if char in "[{")
    decoder = json.JSONDecoder()
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            value, end = decoder.raw_decode(candidate)
        except json.JSONDecodeError:
            continue
        trailing = candidate[end:].strip()
        if trailing and not trailing.startswith("```"):
            continue
        if isinstance(value, (dict, list)):
            return value
    raise ValidationFailure("LLM response is not valid complete JSON")


class GovernedLLMClient:
    """Policy, budget, validation, retry, and audit wrapper around an LLM provider."""

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
        self.provider_responses = 0
        self.structured_output_failures = 0
        self.input_chars = 0
        self.output_chars = 0
        self.estimated_cost_usd = 0.0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.usage_missing_calls = 0
        self.cost_missing_calls = 0

    @property
    def usage_complete(self) -> bool:
        return self.usage_missing_calls == 0

    @property
    def cost_complete(self) -> bool:
        return self.cost_missing_calls == 0

    def generate(self, request: LLMRequest) -> LLMResponse:
        self._validate_request(request)
        current_request = request
        structured = self.policy.require_structured_output and request.output_schema is not None
        max_structured_attempts = 1 + (self.policy.structured_output_retries if structured else 0)
        last_structured_error: LLMStructuredOutputError | None = None

        for structured_attempt in range(max_structured_attempts):
            input_chars = len(current_request.system_instructions) + len(current_request.user_content)
            self._check_pre_call_budget(input_chars=input_chars)
            try:
                response = self.provider.generate(current_request)
            except Exception:
                self._audit(
                    LLMAuditRecord(
                        request_id=current_request.request_id,
                        provider=current_request.provider,
                        model=current_request.model,
                        purpose=current_request.purpose,
                        data_classification=current_request.data_classification,
                        request_sha256=_sha256(
                            current_request.system_instructions + "\n" + current_request.user_content
                        ),
                        prompt_content_recorded=self.policy.record_prompt_content,
                        status="transport_failed",
                        input_chars=input_chars,
                        output_chars=0,
                    )
                )
                raise

            validation_error: str | None = None
            if structured:
                if response.status != "completed":
                    reason = self._incomplete_reason(response)
                    validation_error = (
                        f"Provider response status was {response.status!r}"
                        + (f": {reason}" if reason else "")
                    )
                elif response.parsed is None:
                    try:
                        response.parsed = _extract_json(response.text)
                    except ValidationFailure as exc:
                        validation_error = str(exc)

            self._record_response(
                request=current_request,
                response=response,
                input_chars=input_chars,
                validation_error=validation_error,
            )
            budget_error = self._post_call_budget_error()
            if budget_error is not None:
                raise LLMBudgetExceeded(budget_error)

            if validation_error is None:
                return response

            last_structured_error = LLMStructuredOutputError(validation_error, response)
            can_retry = (
                structured_attempt + 1 < max_structured_attempts
                and response.status != "refused"
            )
            if not can_retry:
                raise last_structured_error
            current_request = self._retry_request(current_request, structured_attempt + 1)

        if last_structured_error is not None:  # pragma: no cover
            raise last_structured_error
        raise LLMAdapterError("Structured-output attempt loop exited unexpectedly")  # pragma: no cover

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

    def _check_pre_call_budget(self, input_chars: int) -> None:
        budget = self.policy.budget
        if self.calls + 1 > budget.max_calls:
            raise LLMBudgetExceeded("LLM call budget exceeded")
        if self.input_chars + input_chars > budget.max_input_chars:
            raise LLMBudgetExceeded("LLM input character budget exceeded")
        if self.output_chars > budget.max_output_chars:
            raise LLMBudgetExceeded("LLM output character budget exceeded")
        if (
            budget.max_estimated_cost_usd is not None
            and self.estimated_cost_usd > budget.max_estimated_cost_usd
        ):
            raise LLMBudgetExceeded("LLM estimated cost budget exceeded")

    def _post_call_budget_error(self) -> str | None:
        budget = self.policy.budget
        if self.output_chars > budget.max_output_chars:
            return "LLM output character budget exceeded after the provider response"
        if (
            budget.max_estimated_cost_usd is not None
            and self.estimated_cost_usd > budget.max_estimated_cost_usd
        ):
            return "LLM estimated cost budget exceeded after the provider response"
        return None

    def _record_response(
        self,
        *,
        request: LLMRequest,
        response: LLMResponse,
        input_chars: int,
        validation_error: str | None,
    ) -> None:
        output_chars = len(response.text)
        self.calls += 1
        self.provider_responses += 1
        self.input_chars += input_chars
        self.output_chars += output_chars

        usage = response.usage
        if usage.input_tokens is None or usage.output_tokens is None:
            self.usage_missing_calls += 1
        else:
            self.input_tokens += usage.input_tokens
            self.output_tokens += usage.output_tokens
            self.total_tokens += usage.total_tokens or (usage.input_tokens + usage.output_tokens)
        if usage.estimated_cost_usd is None:
            self.cost_missing_calls += 1
        else:
            self.estimated_cost_usd += usage.estimated_cost_usd
        if validation_error is not None:
            self.structured_output_failures += 1

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
                status="invalid_structured_output" if validation_error else response.status,
                provider_status=str(response.raw_metadata.get("response_status") or response.status),
                structured_output_valid=None if not request.output_schema else validation_error is None,
                validation_error=validation_error,
                incomplete_reason=self._incomplete_reason(response),
                latency_ms=response.latency_ms,
                attempts=response.attempts,
                input_chars=input_chars,
                output_chars=output_chars,
                usage=response.usage,
            )
        )

    def _retry_request(self, request: LLMRequest, retry_index: int) -> LLMRequest:
        multiplied = int(request.max_output_tokens * self.policy.structured_output_retry_token_multiplier)
        next_tokens = min(
            max(request.max_output_tokens + 1, multiplied),
            self.policy.structured_output_retry_max_tokens,
        )
        metadata = dict(request.metadata)
        metadata["structured_output_retry_index"] = retry_index
        return request.model_copy(
            update={
                "request_id": new_id("llmreq"),
                "system_instructions": (
                    request.system_instructions
                    + " The previous provider response was incomplete or invalid. Return one complete JSON value only, with no prose or code fences."
                ),
                "max_output_tokens": next_tokens,
                "metadata": metadata,
            }
        )

    @staticmethod
    def _incomplete_reason(response: LLMResponse) -> str | None:
        details = response.raw_metadata.get("incomplete_details")
        if isinstance(details, dict):
            reason = details.get("reason")
            return str(reason) if reason else json.dumps(details, sort_keys=True)
        if details:
            return str(details)
        return None

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
            usage=LLMUsage(input_tokens=0, output_tokens=0, total_tokens=0, estimated_cost_usd=0.0),
            latency_ms=round((time.perf_counter() - started) * 1000, 3),
            request_sha256=request_hash,
            output_sha256=_sha256(text),
            raw_metadata={"adapter": "MockLLMAdapter", "response_status": "completed"},
        )


class OpenAIResponsesAdapter:
    """Minimal standard-library adapter for the OpenAI Responses API.

    The adapter stores no API key, records no prompt content, and returns provider
    status/usage even when structured-output validation must fail upstream.
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
                usage_raw = raw.get("usage") or {}
                usage = LLMUsage(
                    input_tokens=usage_raw.get("input_tokens"),
                    output_tokens=usage_raw.get("output_tokens"),
                    total_tokens=usage_raw.get("total_tokens"),
                )
                provider_status = str(raw.get("status") or "completed")
                if refusal:
                    status = "refused"
                elif provider_status == "completed":
                    status = "completed"
                elif provider_status == "incomplete":
                    status = "incomplete"
                else:
                    status = "failed"
                return LLMResponse(
                    request_id=request.request_id,
                    provider=self.name,
                    model=request.model,
                    status=status,
                    text=text,
                    parsed=None,
                    refusal=refusal,
                    usage=usage,
                    latency_ms=round((time.perf_counter() - started) * 1000, 3),
                    attempts=attempts,
                    request_sha256=_sha256(request.system_instructions + "\n" + request.user_content),
                    output_sha256=_sha256(text) if text else None,
                    provider_response_id=raw.get("id"),
                    raw_metadata={
                        "response_status": provider_status,
                        "incomplete_details": raw.get("incomplete_details"),
                    },
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
