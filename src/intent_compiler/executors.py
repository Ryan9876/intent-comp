from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Protocol

from .errors import UnsafeTarget
from .models import ExecutionContract, ExecutionResult


class Executor(Protocol):
    def execute(self, contract: ExecutionContract) -> ExecutionResult: ...


class SafeFileExecutor:
    """Demonstration executor limited to writing one UTF-8 file under a workspace."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

    def _resolve_target(self, target: str) -> Path:
        path = (self.workspace / target).resolve()
        if self.workspace != path and self.workspace not in path.parents:
            raise UnsafeTarget(f"Target escapes approved workspace: {target}")
        return path

    def execute(self, contract: ExecutionContract) -> ExecutionResult:
        started = time.perf_counter()
        if contract.action != "write_text_file":
            raise ValueError(f"Unsupported demonstration action: {contract.action}")
        target = self._resolve_target(contract.exact_target)
        content = contract.inputs.get("content")
        if not isinstance(content, str):
            raise ValueError("write_text_file requires string input 'content'")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        return ExecutionResult(
            contract_id=contract.contract_id,
            upstream_refs=[contract.artifact_id],
            changed_targets=[str(target)],
            observed_state={
                "exists": target.exists(),
                "size": target.stat().st_size,
                "sha256": digest,
            },
            telemetry={"elapsed_ms": elapsed_ms, "executor": "SafeFileExecutor"},
        )
