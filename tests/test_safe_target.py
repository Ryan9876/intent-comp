import pytest

from intent_compiler.enums import ArtifactStatus
from intent_compiler.errors import UnsafeTarget
from intent_compiler.executors import SafeFileExecutor
from intent_compiler.models import ExecutionContract, VerificationCheck


def test_executor_rejects_path_escape(tmp_path):
    contract = ExecutionContract(
        status=ArtifactStatus.APPROVED,
        objective_id="obj",
        actor="actor",
        action="write_text_file",
        exact_target="../escape.txt",
        scope=["../escape.txt"],
        required_authority=["write:workspace"],
        granted_authority=["write:workspace"],
        inputs={"content": "unsafe"},
        expected_outputs=["file"],
        acceptance_criteria=["exists"],
        verification_checks=[VerificationCheck(kind="file_exists", target="../escape.txt", expected=True, description="exists")],
        rollback="delete file",
        completion_evidence=["report"],
        stopping_conditions=["unsafe target"],
    )
    with pytest.raises(UnsafeTarget):
        SafeFileExecutor(tmp_path).execute(contract)
