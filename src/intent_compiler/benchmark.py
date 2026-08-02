from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Approach = Literal[
    "direct_prompt",
    "structured_prompt",
    "simple_chain",
    "intent_compilation",
]


class BenchmarkMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outcome_quality: float = Field(ge=0, le=100)
    factual_error_rate: float = Field(ge=0, le=100)
    requirement_coverage: float = Field(ge=0, le=100)
    execution_success: float = Field(ge=0, le=100)
    rework_minutes: float = Field(ge=0)
    traceability: float = Field(ge=0, le=100)
    human_effort_minutes: float = Field(ge=0)
    latency_seconds: float = Field(ge=0)
    cost_usd: float = Field(ge=0)
    verification_burden_minutes: float = Field(ge=0)


class BenchmarkRun(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str
    domain: str
    approach: Approach
    metrics: BenchmarkMetrics
    notes: str = ""


class BenchmarkHarness:
    def __init__(self) -> None:
        self.runs: list[BenchmarkRun] = []

    def add(self, run: BenchmarkRun) -> None:
        self.runs.append(run)

    def summarize(self) -> dict[str, dict[str, float]]:
        grouped: dict[str, list[BenchmarkMetrics]] = defaultdict(list)
        for run in self.runs:
            grouped[run.approach].append(run.metrics)
        summary: dict[str, dict[str, float]] = {}
        for approach, metrics in grouped.items():
            summary[approach] = {
                field: round(mean(getattr(metric, field) for metric in metrics), 3)
                for field in BenchmarkMetrics.model_fields
            }
        return summary

    def write_summary(self, path: str | Path) -> Path:
        import json

        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(self.summarize(), indent=2), encoding="utf-8")
        return output
