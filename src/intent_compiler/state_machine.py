from .enums import ArtifactStatus
from .errors import InvalidTransition


ALLOWED_TRANSITIONS: dict[ArtifactStatus, set[ArtifactStatus]] = {
    ArtifactStatus.PROPOSED: {
        ArtifactStatus.GENERATED,
        ArtifactStatus.REVIEWED,
        ArtifactStatus.BLOCKED,
        ArtifactStatus.FAILED,
        ArtifactStatus.SUPERSEDED,
    },
    ArtifactStatus.GENERATED: {
        ArtifactStatus.REVIEWED,
        ArtifactStatus.BLOCKED,
        ArtifactStatus.FAILED,
        ArtifactStatus.SUPERSEDED,
    },
    ArtifactStatus.REVIEWED: {
        ArtifactStatus.APPROVED,
        ArtifactStatus.BLOCKED,
        ArtifactStatus.FAILED,
        ArtifactStatus.SUPERSEDED,
    },
    ArtifactStatus.APPROVED: {
        ArtifactStatus.EXECUTING,
        ArtifactStatus.BLOCKED,
        ArtifactStatus.SUPERSEDED,
    },
    ArtifactStatus.EXECUTING: {
        ArtifactStatus.EXECUTED_UNVERIFIED,
        ArtifactStatus.FAILED,
        ArtifactStatus.UNKNOWN,
    },
    ArtifactStatus.EXECUTED_UNVERIFIED: {
        ArtifactStatus.VERIFIED,
        ArtifactStatus.PARTIAL,
        ArtifactStatus.FAILED,
        ArtifactStatus.UNKNOWN,
    },
    ArtifactStatus.VERIFIED: {
        ArtifactStatus.DEPLOYED,
        ArtifactStatus.SUPERSEDED,
    },
    ArtifactStatus.PARTIAL: {
        ArtifactStatus.REVIEWED,
        ArtifactStatus.BLOCKED,
        ArtifactStatus.SUPERSEDED,
    },
    ArtifactStatus.BLOCKED: {
        ArtifactStatus.PROPOSED,
        ArtifactStatus.REVIEWED,
        ArtifactStatus.SUPERSEDED,
    },
    ArtifactStatus.FAILED: {
        ArtifactStatus.PROPOSED,
        ArtifactStatus.SUPERSEDED,
    },
    ArtifactStatus.UNKNOWN: {
        ArtifactStatus.REVIEWED,
        ArtifactStatus.BLOCKED,
        ArtifactStatus.FAILED,
    },
    ArtifactStatus.SUPERSEDED: set(),
    ArtifactStatus.DEPLOYED: {ArtifactStatus.SUPERSEDED},
}


def transition(current: ArtifactStatus, target: ArtifactStatus) -> ArtifactStatus:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransition(f"Cannot transition artifact from {current} to {target}")
    return target
