from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import (
    ArtifactStatus,
    EvidenceClassification,
    StageName,
    VerificationOutcome,
    WorkflowMode,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class ProvenanceRecord(StrictModel):
    source: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    retrieved_at: datetime = Field(default_factory=utc_now)
    authoritative: bool = False
    notes: str = ""


class BaseArtifact(StrictModel):
    artifact_id: str
    artifact_type: str
    version: int = Field(default=1, ge=1)
    status: ArtifactStatus = ArtifactStatus.PROPOSED
    stage: StageName
    upstream_refs: list[str] = Field(default_factory=list)
    provenance: list[ProvenanceRecord] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def touch(self) -> None:
        self.updated_at = utc_now()


class TriageAssessment(StrictModel):
    complexity: int = Field(ge=0, le=2)
    consequence: int = Field(ge=0, le=2)
    ambiguity: int = Field(ge=0, le=2)
    reuse: int = Field(ge=0, le=2)
    evidence_burden: int = Field(ge=0, le=2)
    high_consequence_override: bool = False
    rationale: str = Field(min_length=1)

    @property
    def score(self) -> int:
        return (
            self.complexity
            + self.consequence
            + self.ambiguity
            + self.reuse
            + self.evidence_burden
        )

    @property
    def mode(self) -> WorkflowMode:
        if self.high_consequence_override or self.score >= 6:
            return WorkflowMode.ADVANCED
        if self.score >= 3:
            return WorkflowMode.MINIMUM
        return WorkflowMode.DIRECT


class ObjectiveSpecification(BaseArtifact):
    artifact_id: str = Field(default_factory=lambda: new_id("obj"))
    artifact_type: Literal["objective_specification"] = "objective_specification"
    stage: Literal[StageName.OBJECTIVE] = StageName.OBJECTIVE
    desired_outcome: str = Field(min_length=10)
    primary_user: str = Field(min_length=1)
    stakeholders: list[str] = Field(default_factory=list)
    scope: list[str] = Field(min_length=1)
    non_goals: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(min_length=1)
    consequence_of_failure: str = Field(min_length=1)
    material_unknowns: list[str] = Field(default_factory=list)


class EvidenceEntry(StrictModel):
    evidence_id: str = Field(default_factory=lambda: new_id("ev"))
    claim: str = Field(min_length=1)
    classification: EvidenceClassification
    source: str = Field(min_length=1)
    source_owner: str = Field(min_length=1)
    retrieved_at: datetime = Field(default_factory=utc_now)
    freshness_requirement: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    supports: list[str] = Field(default_factory=list)
    contradicts: list[str] = Field(default_factory=list)
    decision_impact: str = Field(min_length=1)


class EvidenceRegister(BaseArtifact):
    artifact_id: str = Field(default_factory=lambda: new_id("evidence"))
    artifact_type: Literal["evidence_register"] = "evidence_register"
    stage: Literal[StageName.EVIDENCE] = StageName.EVIDENCE
    entries: list[EvidenceEntry] = Field(min_length=1)
    unresolved_contradictions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def facts_require_meaningful_source(self) -> "EvidenceRegister":
        for entry in self.entries:
            if entry.classification == EvidenceClassification.FACT and entry.source.lower() in {
                "model",
                "memory",
                "assumption",
            }:
                raise ValueError(
                    f"Fact {entry.evidence_id} cannot use {entry.source!r} as its source"
                )
        return self


class SolutionOption(StrictModel):
    option_id: str = Field(default_factory=lambda: new_id("option"))
    title: str = Field(min_length=1)
    description: str = Field(min_length=10)
    benefits: list[str] = Field(min_length=1)
    risks: list[str] = Field(default_factory=list)
    cost: str = Field(min_length=1)
    reversibility: str = Field(min_length=1)


class SolutionRecommendation(BaseArtifact):
    artifact_id: str = Field(default_factory=lambda: new_id("design"))
    artifact_type: Literal["solution_recommendation"] = "solution_recommendation"
    stage: Literal[StageName.DESIGN] = StageName.DESIGN
    problem_statement: str = Field(min_length=10)
    options: list[SolutionOption] = Field(min_length=1)
    recommended_option_id: str
    rationale: str = Field(min_length=10)
    risks: list[str] = Field(default_factory=list)
    reconsideration_triggers: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def recommended_option_exists(self) -> "SolutionRecommendation":
        ids = {option.option_id for option in self.options}
        if self.recommended_option_id not in ids:
            raise ValueError("recommended_option_id must reference an option")
        return self


class ActionStep(StrictModel):
    step_id: str = Field(default_factory=lambda: new_id("step"))
    title: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    dependencies: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(min_length=1)
    checkpoint: str = Field(min_length=1)


class ActionPlan(BaseArtifact):
    artifact_id: str = Field(default_factory=lambda: new_id("plan"))
    artifact_type: Literal["action_plan"] = "action_plan"
    stage: Literal[StageName.PLAN] = StageName.PLAN
    objective_id: str = Field(min_length=1)
    steps: list[ActionStep] = Field(min_length=1)
    risks: list[str] = Field(default_factory=list)
    stopping_conditions: list[str] = Field(min_length=1)


class VerificationCheck(StrictModel):
    check_id: str = Field(default_factory=lambda: new_id("check"))
    kind: Literal["file_exists", "text_contains", "sha256", "json_equals"]
    target: str = Field(min_length=1)
    expected: Any = None
    description: str = Field(min_length=1)


class ExecutionContract(BaseArtifact):
    artifact_id: str = Field(default_factory=lambda: new_id("contract"))
    artifact_type: Literal["execution_contract"] = "execution_contract"
    stage: Literal[StageName.CONTRACT] = StageName.CONTRACT
    contract_id: str = Field(default_factory=lambda: new_id("ctr"))
    objective_id: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    action: str = Field(min_length=1)
    exact_target: str = Field(min_length=1)
    scope: list[str] = Field(min_length=1)
    prohibited_scope: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    required_authority: list[str] = Field(min_length=1)
    granted_authority: list[str] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)
    expected_outputs: list[str] = Field(min_length=1)
    acceptance_criteria: list[str] = Field(min_length=1)
    verification_checks: list[VerificationCheck] = Field(min_length=1)
    rollback: str = Field(min_length=1)
    completion_evidence: list[str] = Field(min_length=1)
    stopping_conditions: list[str] = Field(min_length=1)

    @field_validator("scope", "prohibited_scope")
    @classmethod
    def no_blank_scope(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("scope values cannot be blank")
        return values


class ExecutionResult(BaseArtifact):
    artifact_id: str = Field(default_factory=lambda: new_id("execution"))
    artifact_type: Literal["execution_result"] = "execution_result"
    stage: Literal[StageName.EXECUTE] = StageName.EXECUTE
    contract_id: str = Field(min_length=1)
    transaction_id: str = Field(default_factory=lambda: new_id("tx"))
    changed_targets: list[str] = Field(default_factory=list)
    observed_state: dict[str, Any] = Field(default_factory=dict)
    telemetry: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class CheckResult(StrictModel):
    check_id: str
    passed: bool
    observed: Any = None
    message: str


class VerificationReport(BaseArtifact):
    artifact_id: str = Field(default_factory=lambda: new_id("verification"))
    artifact_type: Literal["verification_report"] = "verification_report"
    stage: Literal[StageName.VERIFY] = StageName.VERIFY
    verification_id: str = Field(default_factory=lambda: new_id("vr"))
    contract_id: str = Field(min_length=1)
    expected_state: dict[str, Any] = Field(default_factory=dict)
    observed_state: dict[str, Any] = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)
    check_results: list[CheckResult] = Field(default_factory=list)
    tests_run: list[str] = Field(default_factory=list)
    tests_unrun: list[str] = Field(default_factory=list)
    unverified_items: list[str] = Field(default_factory=list)
    outcome: VerificationOutcome
    corrective_action: str = ""


class LearningRecord(BaseArtifact):
    artifact_id: str = Field(default_factory=lambda: new_id("learning"))
    artifact_type: Literal["learning_record"] = "learning_record"
    stage: Literal[StageName.LEARN] = StageName.LEARN
    workflow_id: str = Field(min_length=1)
    findings: list[str] = Field(min_length=1)
    proposed_changes: list[str] = Field(default_factory=list)
    benchmark_impact: dict[str, float] = Field(default_factory=dict)


class AuditEvent(StrictModel):
    event_id: str = Field(default_factory=lambda: new_id("audit"))
    workflow_id: str
    event_type: str
    actor: str
    timestamp: datetime = Field(default_factory=utc_now)
    artifact_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class WorkflowSnapshot(StrictModel):
    workflow_id: str
    mode: WorkflowMode
    current_stage: StageName
    artifact_ids: dict[StageName, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
