from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Literal

from pydantic import Field, model_validator

from .benchmark import Approach
from .benchmark_execution import (
    BenchmarkExecutionRecord,
    BenchmarkScenario,
    MeasuredBenchmarkRunner,
)
from .models import StrictModel, new_id, utc_now


ScoreDimension = Literal[
    "outcome_quality",
    "completeness",
    "factuality",
    "actionability",
    "traceability",
    "verification_quality",
]


class PricingConfig(StrictModel):
    """Externally supplied model pricing, expressed per one million tokens.

    Pricing is intentionally not hard-coded because it changes independently of the package.
    """

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    input_usd_per_million_tokens: float = Field(ge=0)
    output_usd_per_million_tokens: float = Field(ge=0)
    effective_date: str = Field(min_length=1)
    source: str = Field(min_length=1)

    def estimate(self, input_tokens: int | None, output_tokens: int | None) -> float | None:
        if input_tokens is None or output_tokens is None:
            return None
        value = (
            input_tokens * self.input_usd_per_million_tokens
            + output_tokens * self.output_usd_per_million_tokens
        ) / 1_000_000
        return round(value, 8)


class StudyConfig(StrictModel):
    study_id: str = Field(default_factory=lambda: new_id("study"))
    seed: int = 20260801
    repeats_per_scenario: int = Field(default=1, ge=1, le=100)
    approaches: list[Approach] = Field(
        default_factory=lambda: [
            "direct_prompt",
            "structured_prompt",
            "simple_chain",
            "intent_compilation",
        ],
        min_length=2,
    )
    reviewer_dimensions: list[ScoreDimension] = Field(
        default_factory=lambda: [
            "outcome_quality",
            "completeness",
            "factuality",
            "actionability",
            "traceability",
            "verification_quality",
        ]
    )
    minimum_reviews_per_output: int = Field(default=2, ge=1, le=20)
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())

    @model_validator(mode="after")
    def approaches_are_unique(self) -> "StudyConfig":
        if len(self.approaches) != len(set(self.approaches)):
            raise ValueError("approaches must be unique")
        return self


class ScheduleEntry(StrictModel):
    study_id: str
    run_id: str
    scenario_id: str
    repeat_index: int = Field(ge=1)
    order_position: int = Field(ge=1)
    approach: Approach
    blind_output_id: str


class StudyRunRecord(StrictModel):
    study_id: str
    run_id: str
    repeat_index: int = Field(ge=1)
    order_position: int = Field(ge=1)
    blind_output_id: str
    execution: BenchmarkExecutionRecord
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    historical_cost_usd: float = Field(default=0.0, ge=0)
    attempt_count: int = Field(default=1, ge=1)
    usage_complete: bool | None = None
    cost_complete: bool | None = None
    pricing_source: str | None = None


class BlindReviewPacket(StrictModel):
    blind_output_id: str
    scenario_id: str
    domain: str
    objective: str
    requirements: list[str]
    constraints: list[str]
    answer: str
    assumptions: list[str]
    risks: list[str]
    verification_notes: list[str]
    traceability_refs: list[str]
    reviewer_instructions: str = (
        "Score only the submitted output against the scenario. Do not infer the prompting approach. "
        "Use integers 1-5 for every dimension and record concrete defects."
    )


class ReviewRecord(StrictModel):
    review_id: str = Field(default_factory=lambda: new_id("review"))
    study_id: str
    blind_output_id: str
    reviewer_id: str = Field(min_length=1)
    scores: dict[ScoreDimension, int]
    critical_errors: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    confidence: int = Field(default=3, ge=1, le=5)
    reviewed_at: str = Field(default_factory=lambda: utc_now().isoformat())

    @model_validator(mode="after")
    def scores_are_complete_and_bounded(self) -> "ReviewRecord":
        expected = {
            "outcome_quality",
            "completeness",
            "factuality",
            "actionability",
            "traceability",
            "verification_quality",
        }
        if set(self.scores) != expected:
            missing = sorted(expected - set(self.scores))
            extra = sorted(set(self.scores) - expected)
            raise ValueError(f"review scores mismatch; missing={missing}, extra={extra}")
        if any(score < 1 or score > 5 for score in self.scores.values()):
            raise ValueError("review scores must be between 1 and 5")
        return self

    @property
    def overall_score(self) -> float:
        return round(statistics.mean(self.scores.values()), 4)


class ApproachSummary(StrictModel):
    approach: Approach
    runs: int = Field(ge=0)
    errors: int = Field(ge=0)
    schema_pass_rate: float = Field(ge=0, le=100)
    mean_calls: float = Field(ge=0)
    mean_latency_seconds: float = Field(ge=0)
    mean_input_tokens: float | None = Field(default=None, ge=0)
    mean_output_tokens: float | None = Field(default=None, ge=0)
    mean_cost_usd: float | None = Field(default=None, ge=0)
    mean_requirement_coverage: float = Field(ge=0, le=100)
    mean_traceability_refs: float = Field(ge=0)
    reviewed_outputs: int = Field(ge=0)
    mean_blind_review_score: float | None = Field(default=None, ge=1, le=5)
    blind_review_score_ci95: tuple[float, float] | None = None
    critical_error_rate: float | None = Field(default=None, ge=0, le=100)


class StudySummary(StrictModel):
    study_id: str
    generated_at: str = Field(default_factory=lambda: utc_now().isoformat())
    provider_kind: str
    total_runs: int = Field(ge=0)
    total_reviews: int = Field(ge=0)
    approaches: list[ApproachSummary]
    paired_review_win_rates: dict[str, float] = Field(default_factory=dict)
    interpretation: list[str] = Field(default_factory=list)


def _blind_id(study_id: str, scenario_id: str, repeat_index: int, approach: str) -> str:
    raw = f"{study_id}|{scenario_id}|{repeat_index}|{approach}"
    return "out-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_schedule(config: StudyConfig, scenarios: Iterable[BenchmarkScenario]) -> list[ScheduleEntry]:
    rng = random.Random(config.seed)
    entries: list[ScheduleEntry] = []
    for scenario in sorted(scenarios, key=lambda item: item.scenario_id):
        for repeat_index in range(1, config.repeats_per_scenario + 1):
            approaches = list(config.approaches)
            rng.shuffle(approaches)
            for position, approach in enumerate(approaches, start=1):
                entries.append(
                    ScheduleEntry(
                        study_id=config.study_id,
                        run_id=new_id("run"),
                        scenario_id=scenario.scenario_id,
                        repeat_index=repeat_index,
                        order_position=position,
                        approach=approach,
                        blind_output_id=_blind_id(
                            config.study_id, scenario.scenario_id, repeat_index, approach
                        ),
                    )
                )
    return entries


def run_study(
    config: StudyConfig,
    scenarios: list[BenchmarkScenario],
    runner: MeasuredBenchmarkRunner,
    pricing: PricingConfig | None = None,
) -> tuple[list[ScheduleEntry], list[StudyRunRecord]]:
    scenario_by_id = {item.scenario_id: item for item in scenarios}
    schedule = build_schedule(config, scenarios)
    records: list[StudyRunRecord] = []
    for entry in schedule:
        scenario = scenario_by_id[entry.scenario_id]
        execution = runner.run(scenario, entry.approach)
        output = execution.output
        input_tokens = None
        output_tokens = None
        total_tokens = None
        # Usage is collected at the call audit level. BenchmarkExecutionRecord in v0.3
        # exposes aggregate values when available; getattr preserves compatibility with v0.2 records.
        input_tokens = getattr(execution, "input_tokens", None)
        output_tokens = getattr(execution, "output_tokens", None)
        total_tokens = getattr(execution, "total_tokens", None)
        cost = pricing.estimate(input_tokens, output_tokens) if pricing else None
        records.append(
            StudyRunRecord(
                study_id=config.study_id,
                run_id=entry.run_id,
                repeat_index=entry.repeat_index,
                order_position=entry.order_position,
                blind_output_id=entry.blind_output_id,
                execution=execution,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                usage_complete=execution.usage_complete,
                cost_complete=execution.usage_complete and cost is not None,
                pricing_source=pricing.source if pricing else None,
            )
        )
    return schedule, records


def create_blind_packets(
    records: Iterable[StudyRunRecord],
    scenarios: Iterable[BenchmarkScenario],
) -> tuple[list[BlindReviewPacket], dict[str, dict[str, str | int]]]:
    scenario_by_id = {item.scenario_id: item for item in scenarios}
    packets: list[BlindReviewPacket] = []
    mapping: dict[str, dict[str, str | int]] = {}
    for record in records:
        output = record.execution.output
        if output is None:
            continue
        scenario = scenario_by_id[record.execution.scenario_id]
        packets.append(
            BlindReviewPacket(
                blind_output_id=record.blind_output_id,
                scenario_id=scenario.scenario_id,
                domain=scenario.domain,
                objective=scenario.objective,
                requirements=scenario.requirements,
                constraints=scenario.constraints,
                answer=output.answer,
                assumptions=output.assumptions,
                risks=output.risks,
                verification_notes=output.verification_notes,
                traceability_refs=output.traceability_refs,
            )
        )
        mapping[record.blind_output_id] = {
            "approach": record.execution.approach,
            "run_id": record.run_id,
            "scenario_id": record.execution.scenario_id,
            "repeat_index": record.repeat_index,
        }
    return packets, mapping


def write_jsonl(items: Iterable[StrictModel], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    values = list(items)
    output.write_text(
        "".join(item.model_dump_json() + "\n" for item in values), encoding="utf-8"
    )
    return output


def read_jsonl(path: str | Path, model: type[StrictModel]) -> list[StrictModel]:
    source = Path(path)
    if not source.exists():
        return []
    return [model.model_validate_json(line) for line in source.read_text().splitlines() if line]


def write_mapping(mapping: dict[str, dict[str, str | int]], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(mapping, indent=2, sort_keys=True), encoding="utf-8")
    return output


def write_review_template(
    study_id: str, packets: Iterable[BlindReviewPacket], path: str | Path
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "review_id",
        "study_id",
        "blind_output_id",
        "reviewer_id",
        "outcome_quality",
        "completeness",
        "factuality",
        "actionability",
        "traceability",
        "verification_quality",
        "critical_errors",
        "strengths",
        "confidence",
    ]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for packet in packets:
            writer.writerow(
                {
                    "review_id": "",
                    "study_id": study_id,
                    "blind_output_id": packet.blind_output_id,
                    "reviewer_id": "",
                    "outcome_quality": "",
                    "completeness": "",
                    "factuality": "",
                    "actionability": "",
                    "traceability": "",
                    "verification_quality": "",
                    "critical_errors": "",
                    "strengths": "",
                    "confidence": "",
                }
            )
    return output


def import_reviews_csv(path: str | Path) -> list[ReviewRecord]:
    records: list[ReviewRecord] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if not row.get("reviewer_id"):
                continue
            scores = {
                dimension: int(row[dimension])
                for dimension in [
                    "outcome_quality",
                    "completeness",
                    "factuality",
                    "actionability",
                    "traceability",
                    "verification_quality",
                ]
            }
            records.append(
                ReviewRecord(
                    review_id=row.get("review_id") or new_id("review"),
                    study_id=row["study_id"],
                    blind_output_id=row["blind_output_id"],
                    reviewer_id=row["reviewer_id"],
                    scores=scores,
                    critical_errors=[
                        item.strip()
                        for item in (row.get("critical_errors") or "").split("|")
                        if item.strip()
                    ],
                    strengths=[
                        item.strip()
                        for item in (row.get("strengths") or "").split("|")
                        if item.strip()
                    ],
                    confidence=int(row.get("confidence") or 3),
                )
            )
    return records


def _mean_optional(values: Iterable[int | float | None]) -> float | None:
    filtered = [float(value) for value in values if value is not None]
    return round(statistics.mean(filtered), 6) if filtered else None


def _bootstrap_ci95(values: list[float], seed: int = 20260801, samples: int = 2000) -> tuple[float, float] | None:
    if not values:
        return None
    if len(values) == 1:
        value = round(values[0], 4)
        return value, value
    rng = random.Random(seed)
    means = []
    for _ in range(samples):
        means.append(statistics.mean(rng.choice(values) for _ in values))
    means.sort()
    lower_index = max(0, math.floor(0.025 * (samples - 1)))
    upper_index = min(samples - 1, math.ceil(0.975 * (samples - 1)))
    return round(means[lower_index], 4), round(means[upper_index], 4)


def summarize_study(
    config: StudyConfig,
    records: list[StudyRunRecord],
    reviews: list[ReviewRecord],
    mapping: dict[str, dict[str, str | int]],
) -> StudySummary:
    records_by_approach: dict[Approach, list[StudyRunRecord]] = defaultdict(list)
    for record in records:
        records_by_approach[record.execution.approach].append(record)

    reviews_by_output: dict[str, list[ReviewRecord]] = defaultdict(list)
    for review in reviews:
        reviews_by_output[review.blind_output_id].append(review)

    approach_review_scores: dict[Approach, list[float]] = defaultdict(list)
    approach_critical: dict[Approach, list[bool]] = defaultdict(list)
    output_mean_scores: dict[str, float] = {}
    for blind_output_id, output_reviews in reviews_by_output.items():
        if blind_output_id not in mapping:
            continue
        score = statistics.mean(review.overall_score for review in output_reviews)
        output_mean_scores[blind_output_id] = score
        approach = str(mapping[blind_output_id]["approach"])
        approach_review_scores[approach].append(score)  # type: ignore[arg-type]
        approach_critical[approach].append(  # type: ignore[arg-type]
            any(review.critical_errors for review in output_reviews)
        )

    summaries: list[ApproachSummary] = []
    for approach in config.approaches:
        group = records_by_approach.get(approach, [])
        scores = approach_review_scores.get(approach, [])
        critical_flags = approach_critical.get(approach, [])
        summaries.append(
            ApproachSummary(
                approach=approach,
                runs=len(group),
                errors=sum(bool(record.execution.errors) for record in group),
                schema_pass_rate=round(
                    100 * sum(record.execution.schema_valid for record in group) / len(group), 4
                )
                if group
                else 0,
                mean_calls=round(statistics.mean(record.execution.calls for record in group), 4)
                if group
                else 0,
                mean_latency_seconds=round(
                    statistics.mean(record.execution.latency_seconds for record in group), 6
                )
                if group
                else 0,
                mean_input_tokens=_mean_optional(record.input_tokens for record in group),
                mean_output_tokens=_mean_optional(record.output_tokens for record in group),
                mean_cost_usd=_mean_optional(record.cost_usd for record in group),
                mean_requirement_coverage=round(
                    statistics.mean(record.execution.requirement_coverage for record in group), 4
                )
                if group
                else 0,
                mean_traceability_refs=round(
                    statistics.mean(
                        record.execution.traceability_reference_count for record in group
                    ),
                    4,
                )
                if group
                else 0,
                reviewed_outputs=len(scores),
                mean_blind_review_score=round(statistics.mean(scores), 4) if scores else None,
                blind_review_score_ci95=_bootstrap_ci95(scores, seed=config.seed),
                critical_error_rate=round(100 * sum(critical_flags) / len(critical_flags), 4)
                if critical_flags
                else None,
            )
        )

    paired_win_rates: dict[str, float] = {}
    # Compare outputs within the same scenario/repeat block only after reviews exist.
    block_scores: dict[tuple[str, int], dict[str, float]] = defaultdict(dict)
    for blind_output_id, score in output_mean_scores.items():
        details = mapping[blind_output_id]
        block_scores[(str(details["scenario_id"]), int(details["repeat_index"]))][
            str(details["approach"])
        ] = score
    for left in config.approaches:
        for right in config.approaches:
            if left >= right:
                continue
            comparable = [
                block for block in block_scores.values() if left in block and right in block
            ]
            if comparable:
                wins = sum(block[left] > block[right] for block in comparable)
                ties = sum(block[left] == block[right] for block in comparable)
                paired_win_rates[f"{left}_vs_{right}"] = round(
                    100 * (wins + 0.5 * ties) / len(comparable), 4
                )

    provider_kind = records[0].execution.provider_kind if records else "unknown"
    interpretation = [
        "Randomization controls order effects but does not eliminate reviewer or scenario bias.",
        "Blind review scores are meaningful only when reviewers are independent and unaware of approach identity.",
        "Requirement coverage and schema validity are deterministic process metrics, not substitutes for outcome quality.",
    ]
    if provider_kind == "mock":
        interpretation.append(
            "Mock-provider results validate orchestration, blinding, and analysis plumbing only; they are not model-quality evidence."
        )
    if not reviews:
        interpretation.append(
            "No completed review records were supplied, so no comparative outcome-quality conclusion is supported."
        )
    return StudySummary(
        study_id=config.study_id,
        provider_kind=provider_kind,
        total_runs=len(records),
        total_reviews=len(reviews),
        approaches=summaries,
        paired_review_win_rates=paired_win_rates,
        interpretation=interpretation,
    )
