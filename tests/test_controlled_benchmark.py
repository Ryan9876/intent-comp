from pathlib import Path

from intent_compiler.benchmark_execution import BenchmarkScenario, MeasuredBenchmarkRunner
from intent_compiler.benchmark_study import (
    ReviewRecord,
    StudyConfig,
    build_schedule,
    create_blind_packets,
    summarize_study,
)
from intent_compiler.llm_adapters import GovernedLLMClient, MockLLMAdapter
from intent_compiler.llm_models import LLMBudget, LLMPolicy
from intent_compiler.provider_factory import deterministic_mock_responder


def client():
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


def scenarios():
    return [
        BenchmarkScenario(
            scenario_id="a",
            domain="testing",
            objective="Create a bounded answer for controlled benchmark scenario A.",
            requirements=["Define scope", "Define verification"],
            constraints=["No external actions"],
            authoritative_context=["Test data"],
        ),
        BenchmarkScenario(
            scenario_id="b",
            domain="testing",
            objective="Create a bounded answer for controlled benchmark scenario B.",
            requirements=["Define owner", "Define rollback"],
            constraints=["No external actions"],
            authoritative_context=["Test data"],
        ),
    ]


def test_schedule_is_reproducible_balanced_and_randomized():
    config = StudyConfig(study_id="study-test", seed=42, repeats_per_scenario=2)
    first = build_schedule(config, scenarios())
    second = build_schedule(config, scenarios())
    assert [(x.scenario_id, x.repeat_index, x.order_position, x.approach) for x in first] == [
        (x.scenario_id, x.repeat_index, x.order_position, x.approach) for x in second
    ]
    assert len(first) == 16
    for scenario_id in {x.scenario_id for x in first}:
        for repeat in {1, 2}:
            block = [x for x in first if x.scenario_id == scenario_id and x.repeat_index == repeat]
            assert len(block) == 4
            assert len({x.approach for x in block}) == 4


def test_blind_packet_does_not_expose_approach():
    config = StudyConfig(study_id="study-test", seed=42)
    runner = MeasuredBenchmarkRunner(client(), "mock", "mock-governed-v1")
    schedule = build_schedule(config, scenarios()[:1])
    records = []
    from intent_compiler.benchmark_study import StudyRunRecord
    for entry in schedule:
        execution = runner.run(scenarios()[0], entry.approach)
        records.append(
            StudyRunRecord(
                study_id=config.study_id,
                run_id=entry.run_id,
                repeat_index=entry.repeat_index,
                order_position=entry.order_position,
                blind_output_id=entry.blind_output_id,
                execution=execution,
            )
        )
    packets, mapping = create_blind_packets(records, scenarios()[:1])
    assert packets
    assert "approach" not in packets[0].model_dump()
    serialized = packets[0].model_dump_json()
    assert all(approach not in serialized for approach in config.approaches)
    assert mapping[packets[0].blind_output_id]["approach"] in config.approaches


def test_summary_uses_blind_reviews_and_preserves_mock_warning():
    config = StudyConfig(study_id="study-test", seed=42)
    scenario = scenarios()[0]
    runner = MeasuredBenchmarkRunner(client(), "mock", "mock-governed-v1")
    from intent_compiler.benchmark_study import StudyRunRecord
    schedule = build_schedule(config, [scenario])
    records = []
    for entry in schedule:
        records.append(
            StudyRunRecord(
                study_id=config.study_id,
                run_id=entry.run_id,
                repeat_index=entry.repeat_index,
                order_position=entry.order_position,
                blind_output_id=entry.blind_output_id,
                execution=runner.run(scenario, entry.approach),
            )
        )
    packets, mapping = create_blind_packets(records, [scenario])
    reviews = []
    for packet in packets:
        reviews.append(
            ReviewRecord(
                study_id=config.study_id,
                blind_output_id=packet.blind_output_id,
                reviewer_id="reviewer-1",
                scores={
                    "outcome_quality": 4,
                    "completeness": 4,
                    "factuality": 4,
                    "actionability": 4,
                    "traceability": 4,
                    "verification_quality": 4,
                },
            )
        )
    summary = summarize_study(config, records, reviews, mapping)
    assert summary.total_runs == 4
    assert summary.total_reviews == 4
    assert all(item.mean_blind_review_score == 4 for item in summary.approaches)
    assert any("Mock-provider" in line for line in summary.interpretation)
