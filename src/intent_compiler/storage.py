from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from .llm_models import LLMAuditRecord
from .models import AuditEvent, WorkflowSnapshot

T = TypeVar("T", bound=BaseModel)


class JsonStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.artifacts = self.root / "artifacts"
        self.root.mkdir(parents=True, exist_ok=True)
        self.artifacts.mkdir(parents=True, exist_ok=True)
        self.audit_path = self.root / "audit.jsonl"
        self.snapshot_path = self.root / "workflow.json"
        self.llm_audit_path = self.root / "llm-audit.jsonl"

    def save_artifact(self, artifact: BaseModel) -> Path:
        artifact_id = getattr(artifact, "artifact_id")
        path = self.artifacts / f"{artifact_id}.json"
        path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load_artifact(self, artifact_id: str, model: type[T]) -> T:
        path = self.artifacts / f"{artifact_id}.json"
        return model.model_validate_json(path.read_text(encoding="utf-8"))

    def save_snapshot(self, snapshot: WorkflowSnapshot) -> Path:
        self.snapshot_path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
        return self.snapshot_path

    def load_snapshot(self) -> WorkflowSnapshot:
        return WorkflowSnapshot.model_validate_json(
            self.snapshot_path.read_text(encoding="utf-8")
        )

    def append_audit(self, event: AuditEvent) -> None:
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json() + "\n")

    def read_audit(self) -> list[dict]:
        if not self.audit_path.exists():
            return []
        return [json.loads(line) for line in self.audit_path.read_text().splitlines()]

    def append_llm_audit(self, record: LLMAuditRecord) -> None:
        with self.llm_audit_path.open("a", encoding="utf-8") as handle:
            handle.write(record.model_dump_json() + "\n")

    def read_llm_audit(self) -> list[dict]:
        if not self.llm_audit_path.exists():
            return []
        return [json.loads(line) for line in self.llm_audit_path.read_text().splitlines()]

