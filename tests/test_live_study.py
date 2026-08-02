from pathlib import Path

from intent_compiler.benchmark_execution import BenchmarkScenario, MeasuredBenchmarkRunner
from intent_compiler.benchmark_study import (
    BlindReviewPacket,
    ReviewRecord,
    StudyConfig,
    StudyRunRecord,
    build_schedule,
)
from intent_compiler.live_study import (
    ApprovedModelProfile,
    LiveStudyPolicy,
    assign_reviewers,
    preflight_live_study,
    publication_guard,
    run_resumable_study,
)
from intent_compiler.llm_adapters import GovernedLLMClient, MockLLMAdapter
from intent_compiler.llm_models import LLMBudget, LLMPolicy
from intent_compiler.provider_factory import deterministic_mock_responder


def profile():
    return ApprovedModelProfile(
        provider="openai",
        display_name="GPT-5.6 Terra",
        api_model_id="gpt-5.6-terra",
        approved_for=["controlled benchmark"],
        input_usd_per_million_tokens=2.0,
        output_usd_per_million_tokens=12.0,
        cached_input_usd_per_million_tokens=0.2,
        effective_date="2026-08-02",
        model_source="official model page",
        pricing_source="official pricing page",
        approval_basis="balanced intelligence and cost",
    )


def policy():
    return LiveStudyPolicy(
        max_total_spend_usd=5,
        reserve_per_run_usd=0.25,
        reviewer_ids=["a", "b", "c"],
        minimum_reviews_per_output=2,
    )


def scenarios():
    return [
        BenchmarkScenario(
            scenario_id="s1",
            domain="testing",
            objective="Create a bounded benchmark answer with explicit verification.",
            requirements=["Define scope", "Define verification"],
            constraints=["No external actions"],
            authoritative_context=["Synthetic test scenario"],
        )
    ]


def mock_client():
    return GovernedLLMClient(
        MockLLMAdapter(deterministic_mock_responder),
        LLMPolicy(
            allowed_providers=["mock"],
            allowed_models={"mock": ["mock-governed-v1"]},
            network_access=False,
            permitted_data_classifications=["internal"],
            require_structured_output=True,
            budget=LLMBudget(max_calls=100, max_input_chars=2_000_000, max_output_chars=1_000_000),
        ),
    )


def test_preflight_blocks_without_credential_and_network(tmp_path: Path):
    scenario_path = tmp_path / "scenarios.json"
    scenario_path.write_text("[]", encoding="utf-8")
    config = StudyConfig(study_id="live-test")
    report = preflight_live_study(
        config,
        scenarios(),
        scenario_path,
        profile(),
        policy(),
        credential_configured=False,
        network_allowed=False,
    )
    assert not report.ready_to_run
    assert any("OPENAI_API_KEY" in item for item in report.blockers)
    assert any("Network access" in item for item in report.blockers)
    assert report.content_sent is False


def test_preflight_ready_when_requirements_are_met(tmp_path: Path):
    scenario_path = tmp_path / "scenarios.json"
    scenario_path.write_text("[]", encoding="utf-8")
    report = preflight_live_study(
        StudyConfig(study_id="live-test"),
        scenarios(),
        scenario_path,
        profile(),
        policy(),
        credential_configured=True,
        network_allowed=True,
    )
    assert report.ready_to_run
    assert report.expected_runs == 4
    assert report.projected_max_total_usd == 1.0


def test_reviewer_assignments_are_blind_complete_and_balanced():
    packets = [
        BlindReviewPacket(
            blind_output_id=f"out-{index}",
            scenario_id="s1",
            domain="testing",
            objective="Objective",
            requirements=["R1"],
            constraints=["C1"],
            answer="Answer",
            assumptions=[],
            risks=[],
            verification_notes=[],
            traceability_refs=[],
        )
        for index in range(8)
    ]
    assignments = assign_reviewers("study", packets, policy())
    assert len(assignments) == 16
    by_output = {}
    for assignment in assignments:
        by_output.setdefault(assignment.blind_output_id, set()).add(assignment.reviewer_id)
    assert all(len(reviewers) == 2 for reviewers in by_output.values())
    loads = {}
    for assignment in assignments:
        loads[assignment.reviewer_id] = loads.get(assignment.reviewer_id, 0) + 1
    assert max(loads.values()) - min(loads.values()) <= 1


def test_resumable_runner_skips_completed_records():
    config = StudyConfig(study_id="resume-test")
    runner = MeasuredBenchmarkRunner(mock_client(), "mock", "mock-governed-v1")
    schedule = build_schedule(config, scenarios())
    first = schedule[0]
    execution = runner.run(scenarios()[0], first.approach)
    prior = StudyRunRecord(
        study_id=config.study_id,
        run_id=first.run_id,
        repeat_index=first.repeat_index,
        order_position=first.order_position,
        blind_output_id=first.blind_output_id,
        execution=execution,
        input_tokens=0,
        output_tokens=0,
        total_tokens=0,
        cost_usd=0,
        pricing_source="test",
    )
    result = run_resumable_study(
        config,
        scenarios(),
        MeasuredBenchmarkRunner(mock_client(), "mock", "mock-governed-v1"),
        profile().pricing(),
        policy(),
        [prior],
    )
    assert result.prior_records == 1
    assert result.new_records == 3
    assert len(result.records) == 4


def test_publication_guard_blocks_mock_and_missing_reviews():
    config = StudyConfig(study_id="guard-test")
    runner = MeasuredBenchmarkRunner(mock_client(), "mock", "mock-governed-v1")
    records = []
    for entry in build_schedule(config, scenarios()):
        records.append(
            StudyRunRecord(
                study_id=config.study_id,
                run_id=entry.run_id,
                repeat_index=entry.repeat_index,
                order_position=entry.order_position,
                blind_output_id=entry.blind_output_id,
                execution=runner.run(scenarios()[0], entry.approach),
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cost_usd=0,
                pricing_source="test",
            )
        )
    report = publication_guard(config, records, [], policy(), expected_scenarios=1)
    assert not report.quality_claim_allowed
    assert any("live-provider" in item for item in report.blockers)
    assert any("blind reviews" in item for item in report.blockers)
