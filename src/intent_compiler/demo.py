from __future__ import annotations

import hashlib
from pathlib import Path

from .enums import ArtifactStatus, EvidenceClassification, StageName
from .executors import SafeFileExecutor
from .models import (
    ActionPlan,
    ActionStep,
    EvidenceEntry,
    EvidenceRegister,
    ExecutionContract,
    LearningRecord,
    ObjectiveSpecification,
    SolutionOption,
    SolutionRecommendation,
    TriageAssessment,
    VerificationCheck,
)
from .storage import JsonStore
from .verification import DeterministicVerifier
from .workflow import IntentCompilationWorkflow


def run_demo(workspace: str | Path) -> dict:
    workspace = Path(workspace).resolve()
    store = JsonStore(workspace / ".intent-compiler")
    workflow = IntentCompilationWorkflow(store=store, actor="demo-controller")

    triage = TriageAssessment(
        complexity=1,
        consequence=1,
        ambiguity=1,
        reuse=2,
        evidence_burden=1,
        rationale="Reusable workflow with moderate complexity and verifiable output.",
    )
    mode = workflow.triage(triage)

    objective = ObjectiveSpecification(
        desired_outcome="Create a verified methodology summary file inside the approved workspace.",
        primary_user="methodology practitioner",
        stakeholders=["reviewer"],
        scope=["write one UTF-8 summary file"],
        non_goals=["modify files outside the workspace", "invoke external services"],
        constraints=["local deterministic execution only"],
        success_criteria=["summary file exists", "summary contains the methodology name"],
        consequence_of_failure="No external impact; demonstration must fail safely.",
    )
    workflow.add_objective(objective)
    workflow.approve(StageName.OBJECTIVE, "human-reviewer")

    evidence = EvidenceRegister(
        entries=[
            EvidenceEntry(
                claim="The methodology is finite and artifact-based.",
                classification=EvidenceClassification.DECISION,
                source="Intent Compilation Methodology v1.0",
                source_owner="methodology owner",
                freshness_requirement="current approved version",
                confidence=1.0,
                decision_impact="Defines the demonstration output.",
            )
        ]
    )
    workflow.add_evidence(evidence)
    workflow.approve(StageName.EVIDENCE, "human-reviewer")

    option = SolutionOption(
        title="Safe local file executor",
        description="Write a single summary file inside an isolated local workspace.",
        benefits=["deterministic", "easy to verify", "no external side effects"],
        risks=["does not demonstrate external tool integration"],
        cost="low",
        reversibility="delete the generated file",
    )
    design = SolutionRecommendation(
        problem_statement="Demonstrate the methodology with a bounded executable action.",
        options=[option],
        recommended_option_id=option.option_id,
        rationale="The local file executor proves authorization, state, persistence, and verification without external risk.",
        reconsideration_triggers=["external integration becomes an explicit benchmark requirement"],
    )
    workflow.add_design(design)
    workflow.approve(StageName.DESIGN, "human-reviewer")

    step = ActionStep(
        title="Write and verify summary",
        owner="demo-controller",
        acceptance_criteria=["file exists", "required phrase is present"],
        checkpoint="verify before declaring completion",
    )
    plan = ActionPlan(
        objective_id=objective.artifact_id,
        steps=[step],
        risks=["target path could escape workspace if not validated"],
        stopping_conditions=["verification passes", "authorization missing", "unsafe path detected"],
    )
    workflow.add_plan(plan)
    workflow.approve(StageName.PLAN, "human-reviewer")

    content = (
        "Intent Compilation is a finite, artifact-based workflow that converts "
        "objectives into governed execution and verified outcomes.\n"
    )
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    contract = ExecutionContract(
        objective_id=objective.artifact_id,
        actor="demo-controller",
        action="write_text_file",
        exact_target="output/methodology-summary.txt",
        scope=["output/methodology-summary.txt"],
        prohibited_scope=["../", "/etc", "external services"],
        required_authority=["write:workspace"],
        granted_authority=["write:workspace"],
        inputs={"content": content},
        expected_outputs=["one UTF-8 file"],
        acceptance_criteria=["file exists", "contains 'Intent Compilation'", "sha256 matches"],
        verification_checks=[
            VerificationCheck(
                kind="file_exists",
                target="output/methodology-summary.txt",
                expected=True,
                description="summary file exists",
            ),
            VerificationCheck(
                kind="text_contains",
                target="output/methodology-summary.txt",
                expected="Intent Compilation",
                description="summary identifies the methodology",
            ),
            VerificationCheck(
                kind="sha256",
                target="output/methodology-summary.txt",
                expected=digest,
                description="summary content matches the approved input",
            ),
        ],
        rollback="Delete output/methodology-summary.txt.",
        completion_evidence=["verification report", "audit log"],
        stopping_conditions=["failed authority", "unsafe target", "verification failure"],
    )
    workflow.add_contract(contract)
    workflow.approve(StageName.CONTRACT, "human-approver")

    execution = workflow.execute(SafeFileExecutor(workspace))
    report = workflow.verify(DeterministicVerifier(workspace))

    learning = LearningRecord(
        workflow_id=workflow.workflow_id,
        findings=[
            "The deterministic control plane can execute and verify a bounded action.",
            "External tool adapters remain unimplemented by design.",
        ],
        proposed_changes=["Add a sandboxed HTTP read adapter only when a benchmark requires it."],
        benchmark_impact={"reference_workflow_completed": 1.0},
    )
    workflow.learn(learning)

    return {
        "workflow_id": workflow.workflow_id,
        "mode": mode,
        "current_stage": workflow.current_stage,
        "verification_outcome": report.outcome,
        "verification_status": report.status,
        "changed_targets": execution.changed_targets,
        "store": str(store.root),
    }
