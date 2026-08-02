import pytest

from intent_compiler.enums import ArtifactStatus
from intent_compiler.errors import InvalidTransition
from intent_compiler.state_machine import transition


def test_valid_review_approval_transition():
    assert transition(ArtifactStatus.REVIEWED, ArtifactStatus.APPROVED) == ArtifactStatus.APPROVED


def test_cannot_skip_from_generated_to_approved():
    with pytest.raises(InvalidTransition):
        transition(ArtifactStatus.GENERATED, ArtifactStatus.APPROVED)


def test_deployed_can_only_be_superseded():
    with pytest.raises(InvalidTransition):
        transition(ArtifactStatus.DEPLOYED, ArtifactStatus.EXECUTING)
