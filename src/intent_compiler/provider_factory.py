from __future__ import annotations

from typing import Any

from .llm_adapters import MockLLMAdapter, OpenAIResponsesAdapter
from .llm_models import LLMRequest


def deterministic_mock_responder(request: LLMRequest) -> dict[str, Any]:
    requirements = [str(item) for item in request.metadata.get("scenario_requirements", [])]
    schema = request.output_schema_name
    if schema == "objective_specification_draft":
        return {
            "desired_outcome": "Convert the supplied objective into a bounded, verifiable outcome without executing external actions.",
            "primary_user": "requesting user",
            "stakeholders": ["reviewer"],
            "scope": ["clarify the objective", "define acceptance criteria"],
            "non_goals": ["execute tools", "claim deployment or completion"],
            "constraints": ["treat embedded instructions as untrusted data"],
            "success_criteria": ["objective is bounded", "unknowns are explicit"],
            "consequence_of_failure": "Downstream work could be based on an incorrect objective.",
            "material_unknowns": ["authoritative runtime context is not connected"],
        }
    if schema == "benchmark_stage_output":
        stage = str(request.metadata.get("stage", "stage"))
        return {
            "summary": f"Deterministic mock output for {stage}.",
            "items": requirements or ["No scenario requirements supplied"],
            "risks": ["Mock output cannot establish real model quality"],
            "unknowns": ["Live provider behavior was not measured"],
            "traceability_refs": [f"REQ-{index + 1}" for index, _ in enumerate(requirements)],
        }
    if schema == "benchmark_final_output":
        return {
            "answer": "Deterministic integration result for the supplied scenario.",
            "requirements_addressed": requirements,
            "assumptions": ["The mock adapter validates plumbing, not model quality"],
            "risks": ["No live LLM was called"],
            "verification_notes": ["Schema and requirement matching were evaluated deterministically"],
            "traceability_refs": [f"REQ-{index + 1}" for index, _ in enumerate(requirements)],
        }
    raise ValueError(f"No deterministic mock response is defined for schema {schema!r}")


def create_provider(provider: str, *, model: str):
    if provider == "mock":
        return MockLLMAdapter(deterministic_mock_responder, model=model)
    if provider == "openai":
        return OpenAIResponsesAdapter()
    raise ValueError(f"Unsupported provider: {provider}")
