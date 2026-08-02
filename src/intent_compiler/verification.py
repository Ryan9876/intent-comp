from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .enums import ArtifactStatus, VerificationOutcome
from .errors import UnsafeTarget
from .models import CheckResult, ExecutionContract, ExecutionResult, VerificationReport


class DeterministicVerifier:
    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).resolve()

    def _resolve(self, target: str) -> Path:
        path = (self.workspace / target).resolve()
        if self.workspace != path and self.workspace not in path.parents:
            raise UnsafeTarget(f"Verification target escapes workspace: {target}")
        return path

    def verify(
        self,
        contract: ExecutionContract,
        execution: ExecutionResult,
    ) -> VerificationReport:
        results: list[CheckResult] = []
        for check in contract.verification_checks:
            path = self._resolve(check.target)
            if check.kind == "file_exists":
                observed = path.exists()
                passed = observed is bool(check.expected)
            elif check.kind == "text_contains":
                observed = path.read_text(encoding="utf-8") if path.exists() else None
                passed = isinstance(observed, str) and str(check.expected) in observed
            elif check.kind == "sha256":
                observed = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
                passed = observed == check.expected
            elif check.kind == "json_equals":
                observed = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
                passed = observed == check.expected
            else:  # pragma: no cover - guarded by model literal
                observed = None
                passed = False
            results.append(
                CheckResult(
                    check_id=check.check_id,
                    passed=passed,
                    observed=observed,
                    message=("passed" if passed else f"failed: {check.description}"),
                )
            )

        passed_count = sum(result.passed for result in results)
        if passed_count == len(results):
            outcome = VerificationOutcome.PASS
            artifact_status = ArtifactStatus.VERIFIED
            unverified: list[str] = []
            corrective = ""
        elif passed_count:
            outcome = VerificationOutcome.PARTIAL
            artifact_status = ArtifactStatus.PARTIAL
            unverified = [result.check_id for result in results if not result.passed]
            corrective = "Resolve failed checks and verify again."
        else:
            outcome = VerificationOutcome.FAIL
            artifact_status = ArtifactStatus.FAILED
            unverified = [result.check_id for result in results]
            corrective = "Rollback or repair the execution before proceeding."

        return VerificationReport(
            contract_id=contract.contract_id,
            upstream_refs=[contract.artifact_id, execution.artifact_id],
            status=artifact_status,
            expected_state={"acceptance_criteria": contract.acceptance_criteria},
            observed_state=execution.observed_state,
            evidence=execution.changed_targets,
            check_results=results,
            tests_run=[check.description for check in contract.verification_checks],
            unverified_items=unverified,
            outcome=outcome,
            corrective_action=corrective,
        )
