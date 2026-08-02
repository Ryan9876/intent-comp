from enum import StrEnum


class StageName(StrEnum):
    TRIAGE = "triage"
    OBJECTIVE = "objective"
    EVIDENCE = "evidence"
    DESIGN = "design"
    PLAN = "plan"
    CONTRACT = "contract"
    EXECUTE = "execute"
    VERIFY = "verify"
    LEARN = "learn"


class WorkflowMode(StrEnum):
    DIRECT = "direct_or_structured_prompt"
    MINIMUM = "minimum_viable_methodology"
    ADVANCED = "advanced_enterprise_methodology"


class ArtifactStatus(StrEnum):
    PROPOSED = "proposed"
    GENERATED = "generated"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    EXECUTING = "executing"
    EXECUTED_UNVERIFIED = "executed_unverified"
    VERIFIED = "verified"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    FAILED = "failed"
    UNKNOWN = "unknown"
    SUPERSEDED = "superseded"
    DEPLOYED = "deployed"


class EvidenceClassification(StrEnum):
    FACT = "fact"
    ASSUMPTION = "assumption"
    INTERPRETATION = "interpretation"
    UNKNOWN = "unknown"
    DECISION = "decision"


class VerificationOutcome(StrEnum):
    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"
