from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from .models import StrictModel, new_id, utc_now


DataClassification = Literal["public", "internal", "confidential", "restricted"]
LLMResponseStatus = Literal["completed", "refused", "failed", "incomplete"]


class LLMBudget(StrictModel):
    max_calls: int = Field(default=8, ge=1)
    max_input_chars: int = Field(default=200_000, ge=1)
    max_output_chars: int = Field(default=80_000, ge=1)
    max_estimated_cost_usd: float | None = Field(default=None, ge=0)


class LLMPolicy(StrictModel):
    allowed_providers: list[str] = Field(min_length=1)
    allowed_models: dict[str, list[str]] = Field(default_factory=dict)
    network_access: bool = False
    permitted_data_classifications: list[DataClassification] = Field(
        default_factory=lambda: ["public", "internal"]
    )
    require_structured_output: bool = True
    structured_output_retries: int = Field(default=1, ge=0, le=3)
    structured_output_retry_token_multiplier: float = Field(default=2.0, ge=1.0, le=4.0)
    structured_output_retry_max_tokens: int = Field(default=16_000, ge=1, le=100_000)
    record_prompt_content: bool = False
    timeout_seconds: float = Field(default=60.0, gt=0, le=600)
    max_retries: int = Field(default=2, ge=0, le=8)
    budget: LLMBudget = Field(default_factory=LLMBudget)

    def permits_model(self, provider: str, model: str) -> bool:
        if provider not in self.allowed_providers:
            return False
        allowed = self.allowed_models.get(provider)
        return allowed is None or not allowed or model in allowed


class LLMRequest(StrictModel):
    request_id: str = Field(default_factory=lambda: new_id("llmreq"))
    purpose: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    system_instructions: str = Field(min_length=1)
    user_content: str = Field(min_length=1)
    data_classification: DataClassification = "internal"
    untrusted_input: bool = True
    output_schema_name: str | None = None
    output_schema: dict[str, Any] | None = None
    max_output_tokens: int = Field(default=2000, ge=1, le=100_000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def schema_fields_are_consistent(self) -> "LLMRequest":
        if bool(self.output_schema_name) != bool(self.output_schema):
            raise ValueError("output_schema_name and output_schema must be provided together")
        return self


class LLMUsage(StrictModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)


class LLMResponse(StrictModel):
    response_id: str = Field(default_factory=lambda: new_id("llmresp"))
    request_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    status: LLMResponseStatus
    text: str = ""
    parsed: dict[str, Any] | list[Any] | None = None
    refusal: str | None = None
    usage: LLMUsage = Field(default_factory=LLMUsage)
    latency_ms: float = Field(ge=0)
    attempts: int = Field(default=1, ge=1)
    request_sha256: str = Field(min_length=64, max_length=64)
    output_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    provider_response_id: str | None = None
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    completed_at: datetime = Field(default_factory=utc_now)


class LLMAuditRecord(StrictModel):
    request_id: str
    response_id: str | None = None
    provider: str
    model: str
    purpose: str
    data_classification: DataClassification
    request_sha256: str
    output_sha256: str | None = None
    prompt_content_recorded: bool = False
    status: str
    provider_status: str | None = None
    structured_output_valid: bool | None = None
    validation_error: str | None = None
    incomplete_reason: str | None = None
    latency_ms: float | None = None
    attempts: int = 0
    input_chars: int = Field(ge=0)
    output_chars: int = Field(ge=0)
    usage: LLMUsage = Field(default_factory=LLMUsage)
    timestamp: datetime = Field(default_factory=utc_now)
