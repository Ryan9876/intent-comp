from __future__ import annotations

import hashlib
import json
import os
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Literal

from pydantic import Field, model_validator

from .benchmark_execution import BenchmarkScenario, MeasuredBenchmarkRunner
from .benchmark_study import (
    BlindReviewPacket,
    PricingConfig,
    ReviewRecord,
    ScheduleEntry,
    StudyConfig,
    StudyRunRecord,
    build_schedule,
)
from .models import StrictModel, new_id, utc_now


class ApprovedModelProfile(StrictModel):
    provider: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    api_model_id: str = Field(min_length=1)
    approved_for: list[str] = Field(min_length=1)
    input_usd_per_million_tokens: float = Field(ge=0)
    output_usd_per_million_tokens: float = Field(ge=0)
    cached_input_usd_per_million_tokens: float | None = Field(default=None, ge=0)
    effective_date: str = Field(min_length=1)
    model_source: str = Field(min_length=1)
    pricing_source: str = Field(min_length=1)
    approval_basis: str = Field(min_length=1)

    def pricing(self) -> PricingConfig:
        return PricingConfig(
            provider=self.provider,
            model=self.api_model_id,
            input_usd_per_million_tokens=self.input_usd_per_million_tokens,
            output_usd_per_million_tokens=self.output_usd_per_million_tokens,
            effective_date=self.effective_date,
            source=self.pricing_source,
        )


class LiveStudyPolicy(StrictModel):
    max_total_spend_usd: float = Field(default=5.0, gt=0)
    reserve_per_run_usd: float = Field(default=0.25, gt=0)
    max_runs: int = Field(default=100, ge=1)
    minimum_reviews_per_output: int = Field(default=2, ge=1, le=20)
    reviewer_ids: list[str] = Field(min_length=2)
    assignment_seed: int = 20260802
    require_exact_token_usage: bool = True
    require_zero_execution_errors: bool = True
    require_complete_blind_review: bool = True
    prohibit_quality_claims_for_mock: bool = True

    @model_validator(mode="after")
    def reviewers_are_unique(self) -> "LiveStudyPolicy":
        if len(set(self.reviewer_ids)) != len(self.reviewer_ids):
            raise ValueError("reviewer_ids must be unique")
        if self.minimum_reviews_per_output > len(self.reviewer_ids):
            raise ValueError("minimum_reviews_per_output cannot exceed reviewer count")
        return self


class PreflightReport(StrictModel):
    generated_at: str = Field(default_factory=lambda: utc_now().isoformat())
    study_id: str
    provider: str
    model: str
    credential_configured: bool
    network_allowed: bool
    expected_runs: int = Field(ge=0)
    completed_runs: int = Field(ge=0)
    remaining_runs: int = Field(ge=0)
    existing_cost_usd: float = Field(ge=0)
    reserved_remaining_cost_usd: float = Field(ge=0)
    projected_max_total_usd: float = Field(ge=0)
    spend_limit_usd: float = Field(gt=0)
    scenario_sha256: str
    ready_to_run: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    content_sent: bool = False


class ResumeResult(StrictModel):
    study_id: str
    total_schedule_entries: int = Field(ge=0)
    prior_records: int = Field(ge=0)
    new_records: int = Field(ge=0)
    skipped_completed: int = Field(ge=0)
    stopped_for_budget: bool = False
    cumulative_cost_usd: float = Field(ge=0)
    records: list[StudyRunRecord]


class ReviewerAssignment(StrictModel):
    assignment_id: str = Field(default_factory=lambda: new_id("assign"))
    study_id: str
    blind_output_id: str
    reviewer_id: str
    assigned_at: str = Field(default_factory=lambda: utc_now().isoformat())


class PublicationGuardReport(StrictModel):
    generated_at: str = Field(default_factory=lambda: utc_now().isoformat())
    study_id: str
    expected_runs: int = Field(ge=0)
    completed_runs: int = Field(ge=0)
    provider_kind: str
    total_cost_usd: float = Field(ge=0)
    spend_limit_usd: float = Field(gt=0)
    execution_errors: int = Field(ge=0)
    outputs_with_sufficient_reviews: int = Field(ge=0)
    outputs_requiring_reviews: int = Field(ge=0)
    exact_usage_complete: bool
    quality_claim_allowed: bool
    methodology_superiority_claim_allowed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _known_cost(records: Iterable[StudyRunRecord]) -> float:
    return round(sum(record.cost_usd or 0.0 for record in records), 8)


def preflight_live_study(
    config: StudyConfig,
    scenarios: list[BenchmarkScenario],
    scenario_path: str | Path,
    profile: ApprovedModelProfile,
    policy: LiveStudyPolicy,
    *,
    credential_configured: bool | None = None,
    network_allowed: bool,
    existing_records: Iterable[StudyRunRecord] = (),
) -> PreflightReport:
    records = list(existing_records)
    credential = bool(os.getenv("OPENAI_API_KEY")) if credential_configured is None else credential_configured
    schedule = build_schedule(config, scenarios)
    completed_ids = {record.blind_output_id for record in records}
    remaining = [entry for entry in schedule if entry.blind_output_id not in completed_ids]
    existing_cost = _known_cost(records)
    reserved = round(len(remaining) * policy.reserve_per_run_usd, 8)
    projected = round(existing_cost + reserved, 8)
    blockers: list[str] = []
    warnings: list[str] = []
    if profile.provider != "openai":
        blockers.append("The approved live-study profile must use the OpenAI provider.")
    if not credential:
        blockers.append("OPENAI_API_KEY is not configured.")
    if not network_allowed:
        blockers.append("Network access is not explicitly allowed.")
    if len(schedule) > policy.max_runs:
        blockers.append(f"Scheduled runs {len(schedule)} exceed policy maximum {policy.max_runs}.")
    if projected > policy.max_total_spend_usd:
        blockers.append(
            f"Reserved maximum ${projected:.2f} exceeds spend limit ${policy.max_total_spend_usd:.2f}."
        )
    if not profile.effective_date:
        blockers.append("Pricing effective date is missing.")
    if not profile.model_source or not profile.pricing_source:
        blockers.append("Official model and pricing sources are required.")
    if records and any(record.execution.provider_kind != "live" for record in records):
        warnings.append("Existing records include non-live runs; they cannot support live quality claims.")
    return PreflightReport(
        study_id=config.study_id,
        provider=profile.provider,
        model=profile.api_model_id,
        credential_configured=credential,
        network_allowed=network_allowed,
        expected_runs=len(schedule),
        completed_runs=len(completed_ids),
        remaining_runs=len(remaining),
        existing_cost_usd=existing_cost,
        reserved_remaining_cost_usd=reserved,
        projected_max_total_usd=projected,
        spend_limit_usd=policy.max_total_spend_usd,
        scenario_sha256=sha256_file(scenario_path),
        ready_to_run=not blockers,
        blockers=blockers,
        warnings=warnings,
    )


def run_resumable_study(
    config: StudyConfig,
    scenarios: list[BenchmarkScenario],
    runner: MeasuredBenchmarkRunner,
    pricing: PricingConfig,
    policy: LiveStudyPolicy,
    existing_records: Iterable[StudyRunRecord] = (),
) -> ResumeResult:
    prior = list(existing_records)
    by_blind_id = {record.blind_output_id: record for record in prior}
    scenario_by_id = {scenario.scenario_id: scenario for scenario in scenarios}
    schedule = build_schedule(config, scenarios)
    new_records: list[StudyRunRecord] = []
    stopped = False
    cumulative_cost = _known_cost(prior)
    for entry in schedule:
        if entry.blind_output_id in by_blind_id:
            continue
        if cumulative_cost + policy.reserve_per_run_usd > policy.max_total_spend_usd:
            stopped = True
            break
        execution = runner.run(scenario_by_id[entry.scenario_id], entry.approach)
        cost = pricing.estimate(execution.input_tokens, execution.output_tokens)
        if cost is None:
            cost = execution.estimated_cost_usd
        record = StudyRunRecord(
            study_id=config.study_id,
            run_id=entry.run_id,
            repeat_index=entry.repeat_index,
            order_position=entry.order_position,
            blind_output_id=entry.blind_output_id,
            execution=execution,
            input_tokens=execution.input_tokens,
            output_tokens=execution.output_tokens,
            total_tokens=execution.total_tokens,
            cost_usd=cost,
            pricing_source=pricing.source,
        )
        new_records.append(record)
        by_blind_id[entry.blind_output_id] = record
        cumulative_cost = round(cumulative_cost + (cost or 0.0), 8)
        if cumulative_cost > policy.max_total_spend_usd:
            stopped = True
            break
    combined = [by_blind_id[key] for key in sorted(by_blind_id)]
    return ResumeResult(
        study_id=config.study_id,
        total_schedule_entries=len(schedule),
        prior_records=len(prior),
        new_records=len(new_records),
        skipped_completed=len(prior),
        stopped_for_budget=stopped,
        cumulative_cost_usd=cumulative_cost,
        records=combined,
    )


def assign_reviewers(
    study_id: str,
    packets: list[BlindReviewPacket],
    policy: LiveStudyPolicy,
) -> list[ReviewerAssignment]:
    rng = random.Random(policy.assignment_seed)
    reviewer_ids = list(policy.reviewer_ids)
    assignments: list[ReviewerAssignment] = []
    load = Counter({reviewer_id: 0 for reviewer_id in reviewer_ids})
    packets_order = list(packets)
    rng.shuffle(packets_order)
    for packet in packets_order:
        eligible = sorted(reviewer_ids, key=lambda reviewer_id: (load[reviewer_id], rng.random()))
        selected = eligible[: policy.minimum_reviews_per_output]
        for reviewer_id in selected:
            assignments.append(
                ReviewerAssignment(
                    study_id=study_id,
                    blind_output_id=packet.blind_output_id,
                    reviewer_id=reviewer_id,
                )
            )
            load[reviewer_id] += 1
    return sorted(assignments, key=lambda item: (item.blind_output_id, item.reviewer_id))


def publication_guard(
    config: StudyConfig,
    records: list[StudyRunRecord],
    reviews: list[ReviewRecord],
    policy: LiveStudyPolicy,
    *,
    expected_scenarios: int | None = None,
) -> PublicationGuardReport:
    scenario_repeat_pairs = {(r.execution.scenario_id, r.repeat_index) for r in records}
    if expected_scenarios is not None:
        expected = expected_scenarios * config.repeats_per_scenario * len(config.approaches)
    elif scenario_repeat_pairs:
        expected = len(scenario_repeat_pairs) * len(config.approaches)
    else:
        expected = 0
    provider_kinds = {record.execution.provider_kind for record in records}
    provider_kind = next(iter(provider_kinds)) if len(provider_kinds) == 1 else "mixed"
    errors = sum(1 for record in records if record.execution.errors)
    total_cost = _known_cost(records)
    exact_usage = all(
        record.input_tokens is not None
        and record.output_tokens is not None
        and record.total_tokens is not None
        and record.cost_usd is not None
        for record in records
    ) if records else False
    review_counts = Counter(review.blind_output_id for review in reviews)
    required_ids = {record.blind_output_id for record in records}
    sufficient = sum(
        1 for blind_id in required_ids if review_counts[blind_id] >= policy.minimum_reviews_per_output
    )
    blockers: list[str] = []
    warnings: list[str] = []
    if provider_kind != "live":
        blockers.append("Only live-provider records can support outcome-quality claims.")
    if len(records) != expected:
        blockers.append(f"Study is incomplete: {len(records)} of {expected} expected runs are present.")
    if policy.require_zero_execution_errors and errors:
        blockers.append(f"{errors} run records contain execution errors.")
    if policy.require_exact_token_usage and not exact_usage:
        blockers.append("Exact token and cost usage is incomplete.")
    if total_cost > policy.max_total_spend_usd:
        blockers.append("Recorded study cost exceeds the approved spend limit.")
    if policy.require_complete_blind_review and sufficient != len(required_ids):
        blockers.append(
            f"Only {sufficient} of {len(required_ids)} outputs have the required blind reviews."
        )
    if not reviews:
        warnings.append("No independent reviews were supplied.")
    quality_allowed = not blockers
    superiority_allowed = quality_allowed and len(required_ids) > 0
    return PublicationGuardReport(
        study_id=config.study_id,
        expected_runs=expected,
        completed_runs=len(records),
        provider_kind=provider_kind,
        total_cost_usd=total_cost,
        spend_limit_usd=policy.max_total_spend_usd,
        execution_errors=errors,
        outputs_with_sufficient_reviews=sufficient,
        outputs_requiring_reviews=len(required_ids),
        exact_usage_complete=exact_usage,
        quality_claim_allowed=quality_allowed,
        methodology_superiority_claim_allowed=superiority_allowed,
        blockers=blockers,
        warnings=warnings,
    )


def write_json(value: StrictModel | list[StrictModel] | dict, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, list):
        data = [item.model_dump(mode="json") if isinstance(item, StrictModel) else item for item in value]
    elif isinstance(value, StrictModel):
        data = value.model_dump(mode="json")
    else:
        data = value
    output.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return output
