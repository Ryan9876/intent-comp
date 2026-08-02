from __future__ import annotations

from collections import defaultdict

from .enums import ArtifactStatus, EvidenceClassification
from .errors import AuthorizationFailure, PrerequisiteFailure, ValidationFailure
from .models import (
    ActionPlan,
    EvidenceRegister,
    ExecutionContract,
    ObjectiveSpecification,
    SolutionRecommendation,
)


def validate_objective(artifact: ObjectiveSpecification) -> None:
    if not artifact.scope:
        raise ValidationFailure("Objective requires scope")
    if not artifact.success_criteria:
        raise ValidationFailure("Objective requires success criteria")
    if artifact.desired_outcome.strip().endswith("?"):
        raise ValidationFailure("Desired outcome should be stated as an outcome, not a question")


def validate_evidence(artifact: EvidenceRegister) -> None:
    if not artifact.entries:
        raise ValidationFailure("Evidence register cannot be empty")
    for entry in artifact.entries:
        if entry.classification == EvidenceClassification.FACT and entry.confidence < 0.5:
            raise ValidationFailure(
                f"Low-confidence item {entry.evidence_id} cannot be classified as fact"
            )
        if entry.classification != EvidenceClassification.ASSUMPTION and not entry.source:
            raise ValidationFailure(f"Evidence {entry.evidence_id} requires a source")


def validate_design(artifact: SolutionRecommendation) -> None:
    if len(artifact.options) < 1:
        raise ValidationFailure("At least one solution option is required")
    if not artifact.rationale.strip():
        raise ValidationFailure("Recommendation requires rationale")


def validate_plan(artifact: ActionPlan) -> None:
    step_ids = {step.step_id for step in artifact.steps}
    if len(step_ids) != len(artifact.steps):
        raise ValidationFailure("Action plan step IDs must be unique")
    graph: dict[str, list[str]] = defaultdict(list)
    for step in artifact.steps:
        for dependency in step.dependencies:
            if dependency not in step_ids:
                raise ValidationFailure(
                    f"Step {step.step_id} references missing dependency {dependency}"
                )
            graph[step.step_id].append(dependency)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise ValidationFailure("Action plan contains a dependency cycle")
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph[node]:
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for step_id in step_ids:
        visit(step_id)


def validate_contract(artifact: ExecutionContract) -> None:
    overlap = set(artifact.scope) & set(artifact.prohibited_scope)
    if overlap:
        raise ValidationFailure(f"Scope conflicts with prohibited scope: {sorted(overlap)}")
    if not artifact.rollback.strip():
        raise ValidationFailure("Execution contract requires rollback or forward-repair guidance")
    if not artifact.verification_checks:
        raise ValidationFailure("Execution contract requires deterministic verification checks")


def validate_authorization(contract: ExecutionContract) -> None:
    if contract.status != ArtifactStatus.APPROVED:
        raise AuthorizationFailure("Execution contract must be approved before execution")
    missing = set(contract.required_authority) - set(contract.granted_authority)
    if missing:
        raise AuthorizationFailure(f"Missing required authority: {sorted(missing)}")


def require_approved(*artifacts) -> None:
    invalid = [
        artifact.artifact_id
        for artifact in artifacts
        if artifact.status not in {ArtifactStatus.APPROVED, ArtifactStatus.VERIFIED}
    ]
    if invalid:
        raise PrerequisiteFailure(f"Upstream artifacts not approved or verified: {invalid}")
