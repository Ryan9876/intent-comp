from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from .enums import ArtifactStatus, StageName, WorkflowMode
from .errors import PrerequisiteFailure, UnknownExecutionState
from .executors import Executor
from .models import (
    ActionPlan,
    AuditEvent,
    BaseArtifact,
    EvidenceRegister,
    ExecutionContract,
    ExecutionResult,
    LearningRecord,
    ObjectiveSpecification,
    SolutionRecommendation,
    TriageAssessment,
    VerificationReport,
    WorkflowSnapshot,
)
from .state_machine import transition
from .storage import JsonStore
from .validators import (
    require_approved,
    validate_authorization,
    validate_contract,
    validate_design,
    validate_evidence,
    validate_objective,
    validate_plan,
)
from .verification import DeterministicVerifier


STAGE_ORDER = [
    StageName.OBJECTIVE,
    StageName.EVIDENCE,
    StageName.DESIGN,
    StageName.PLAN,
    StageName.CONTRACT,
    StageName.EXECUTE,
    StageName.VERIFY,
    StageName.LEARN,
]


class IntentCompilationWorkflow:
    def __init__(self, store: JsonStore, actor: str = "workflow-controller") -> None:
        self.store = store
        self.actor = actor
        self.workflow_id = f"workflow-{uuid4().hex[:12]}"
        self.mode = WorkflowMode.MINIMUM
        self.current_stage = StageName.TRIAGE
        self.artifacts: dict[StageName, BaseArtifact] = {}
        self._persist_snapshot()

    def triage(self, assessment: TriageAssessment) -> WorkflowMode:
        self.mode = assessment.mode
        self._audit(
            "triage_completed",
            details={"score": assessment.score, "mode": self.mode, "rationale": assessment.rationale},
        )
        self._persist_snapshot()
        return self.mode

    def add_objective(self, artifact: ObjectiveSpecification) -> None:
        validate_objective(artifact)
        self._register(StageName.OBJECTIVE, artifact)

    def add_evidence(self, artifact: EvidenceRegister) -> None:
        self._require_stage(StageName.OBJECTIVE)
        validate_evidence(artifact)
        artifact.upstream_refs = [self.artifacts[StageName.OBJECTIVE].artifact_id]
        self._register(StageName.EVIDENCE, artifact)

    def add_design(self, artifact: SolutionRecommendation) -> None:
        self._require_stage(StageName.EVIDENCE)
        validate_design(artifact)
        artifact.upstream_refs = [
            self.artifacts[StageName.OBJECTIVE].artifact_id,
            self.artifacts[StageName.EVIDENCE].artifact_id,
        ]
        self._register(StageName.DESIGN, artifact)

    def add_plan(self, artifact: ActionPlan) -> None:
        self._require_stage(StageName.DESIGN)
        validate_plan(artifact)
        artifact.upstream_refs = [
            self.artifacts[StageName.OBJECTIVE].artifact_id,
            self.artifacts[StageName.DESIGN].artifact_id,
        ]
        self._register(StageName.PLAN, artifact)

    def add_contract(self, artifact: ExecutionContract) -> None:
        self._require_stage(StageName.PLAN)
        validate_contract(artifact)
        artifact.upstream_refs = [
            self.artifacts[StageName.OBJECTIVE].artifact_id,
            self.artifacts[StageName.PLAN].artifact_id,
        ]
        self._register(StageName.CONTRACT, artifact)

    def transition_artifact(
        self,
        stage: StageName,
        target: ArtifactStatus,
        reviewer: str | None = None,
    ) -> BaseArtifact:
        artifact = self.artifacts[stage]
        artifact.status = transition(artifact.status, target)
        artifact.touch()
        self.store.save_artifact(artifact)
        self._audit(
            "artifact_transitioned",
            actor=reviewer or self.actor,
            artifact=artifact,
            details={"target_status": target},
        )
        return artifact

    def approve(self, stage: StageName, reviewer: str) -> BaseArtifact:
        artifact = self.artifacts[stage]
        if artifact.status == ArtifactStatus.PROPOSED:
            self.transition_artifact(stage, ArtifactStatus.REVIEWED, reviewer)
        elif artifact.status == ArtifactStatus.GENERATED:
            self.transition_artifact(stage, ArtifactStatus.REVIEWED, reviewer)
        if artifact.status != ArtifactStatus.REVIEWED:
            raise PrerequisiteFailure(
                f"Artifact {artifact.artifact_id} must be reviewed before approval"
            )
        return self.transition_artifact(stage, ArtifactStatus.APPROVED, reviewer)

    def execute(self, executor: Executor) -> ExecutionResult:
        self._require_stage(StageName.CONTRACT)
        contract = self.artifacts[StageName.CONTRACT]
        assert isinstance(contract, ExecutionContract)
        require_approved(
            self.artifacts[StageName.OBJECTIVE],
            self.artifacts[StageName.EVIDENCE],
            self.artifacts[StageName.DESIGN],
            self.artifacts[StageName.PLAN],
            contract,
        )
        validate_authorization(contract)
        self.transition_artifact(StageName.CONTRACT, ArtifactStatus.EXECUTING)
        try:
            execution = executor.execute(contract)
        except UnknownExecutionState:
            self.transition_artifact(StageName.CONTRACT, ArtifactStatus.UNKNOWN)
            raise
        except Exception as exc:
            self.transition_artifact(StageName.CONTRACT, ArtifactStatus.FAILED)
            self._audit("execution_failed", artifact=contract, details={"error": str(exc)})
            raise
        self.transition_artifact(StageName.CONTRACT, ArtifactStatus.EXECUTED_UNVERIFIED)
        execution.status = ArtifactStatus.EXECUTED_UNVERIFIED
        self._register(StageName.EXECUTE, execution)
        return execution

    def verify(self, verifier: DeterministicVerifier) -> VerificationReport:
        self._require_stage(StageName.EXECUTE)
        contract = self.artifacts[StageName.CONTRACT]
        execution = self.artifacts[StageName.EXECUTE]
        assert isinstance(contract, ExecutionContract)
        assert isinstance(execution, ExecutionResult)
        report = verifier.verify(contract, execution)
        self._register(StageName.VERIFY, report)
        if report.status == ArtifactStatus.VERIFIED:
            contract.status = transition(contract.status, ArtifactStatus.VERIFIED)
            contract.touch()
            self.store.save_artifact(contract)
        return report

    def learn(self, record: LearningRecord) -> None:
        self._require_stage(StageName.VERIFY)
        record.upstream_refs = [self.artifacts[StageName.VERIFY].artifact_id]
        self._register(StageName.LEARN, record)

    def _register(self, stage: StageName, artifact: BaseArtifact) -> None:
        if stage in self.artifacts:
            previous = self.artifacts[stage]
            if previous.status != ArtifactStatus.SUPERSEDED:
                try:
                    previous.status = transition(previous.status, ArtifactStatus.SUPERSEDED)
                except Exception as exc:
                    raise PrerequisiteFailure(
                        f"Existing {stage} artifact must be supersedable: {exc}"
                    ) from exc
                previous.touch()
                self.store.save_artifact(previous)
        if artifact.status == ArtifactStatus.PROPOSED:
            artifact.status = ArtifactStatus.GENERATED
        artifact.touch()
        self.artifacts[stage] = artifact
        self.current_stage = stage
        self.store.save_artifact(artifact)
        self._audit("artifact_registered", artifact=artifact)
        self._persist_snapshot()

    def _require_stage(self, stage: StageName) -> None:
        if stage not in self.artifacts:
            raise PrerequisiteFailure(f"Required stage is missing: {stage}")

    def _audit(
        self,
        event_type: str,
        actor: str | None = None,
        artifact: BaseArtifact | None = None,
        details: dict | None = None,
    ) -> None:
        self.store.append_audit(
            AuditEvent(
                workflow_id=self.workflow_id,
                event_type=event_type,
                actor=actor or self.actor,
                artifact_id=artifact.artifact_id if artifact else None,
                details=details or {},
            )
        )

    def _persist_snapshot(self) -> None:
        self.store.save_snapshot(
            WorkflowSnapshot(
                workflow_id=self.workflow_id,
                mode=self.mode,
                current_stage=self.current_stage,
                artifact_ids={stage: artifact.artifact_id for stage, artifact in self.artifacts.items()},
            )
        )
