from intent_compiler.enums import WorkflowMode
from intent_compiler.models import TriageAssessment


def test_triage_direct():
    assessment = TriageAssessment(
        complexity=0,
        consequence=0,
        ambiguity=1,
        reuse=0,
        evidence_burden=0,
        rationale="simple",
    )
    assert assessment.score == 1
    assert assessment.mode == WorkflowMode.DIRECT


def test_triage_minimum():
    assessment = TriageAssessment(
        complexity=1,
        consequence=1,
        ambiguity=1,
        reuse=0,
        evidence_burden=0,
        rationale="moderate",
    )
    assert assessment.mode == WorkflowMode.MINIMUM


def test_triage_override_forces_advanced():
    assessment = TriageAssessment(
        complexity=0,
        consequence=0,
        ambiguity=0,
        reuse=0,
        evidence_burden=0,
        high_consequence_override=True,
        rationale="security-sensitive override",
    )
    assert assessment.mode == WorkflowMode.ADVANCED
