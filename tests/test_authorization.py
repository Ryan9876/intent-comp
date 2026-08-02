import pytest

from intent_compiler.enums import ArtifactStatus
from intent_compiler.errors import AuthorizationFailure
from intent_compiler.models import ExecutionContract, VerificationCheck
from intent_compiler.validators import validate_authorization


def contract(**overrides):
    data = dict(
        objective_id="obj",
        actor="actor",
        action="write_text_file",
        exact_target="a.txt",
        scope=["a.txt"],
        required_authority=["write:workspace"],
        inputs={"content": "hello"},
        expected_outputs=["file"],
        acceptance_criteria=["exists"],
        verification_checks=[
            VerificationCheck(kind="file_exists", target="a.txt", expected=True, description="exists")
        ],
        rollback="delete file",
        completion_evidence=["report"],
        stopping_conditions=["failure"],
    )
    data.update(overrides)
    return ExecutionContract(**data)


def test_contract_requires_approval():
    with pytest.raises(AuthorizationFailure, match="approved"):
        validate_authorization(contract(granted_authority=["write:workspace"]))


def test_contract_requires_all_authority():
    item = contract(status=ArtifactStatus.APPROVED, granted_authority=[])
    with pytest.raises(AuthorizationFailure, match="Missing"):
        validate_authorization(item)


def test_authorized_contract_passes():
    item = contract(
        status=ArtifactStatus.APPROVED,
        granted_authority=["write:workspace"],
    )
    validate_authorization(item)
