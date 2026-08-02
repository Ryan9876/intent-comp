from intent_compiler.benchmark_execution import BenchmarkScenario, MeasuredBenchmarkRunner
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
            budget=LLMBudget(max_calls=40, max_input_chars=500_000, max_output_chars=200_000),
        ),
    )


def scenario():
    return BenchmarkScenario(
        scenario_id="test-scenario",
        domain="testing",
        objective="Create a bounded plan with requirements and verification for a test scenario.",
        requirements=["Define scope", "Define verification"],
        constraints=["No external actions"],
        authoritative_context=["This is a deterministic integration test"],
    )


def test_intent_compilation_benchmark_records_measured_calls_and_coverage():
    runner = MeasuredBenchmarkRunner(client(), "mock", "mock-governed-v1")
    record = runner.run(scenario(), "intent_compilation")
    assert record.provider_kind == "mock"
    assert record.calls == 6
    assert record.schema_valid is True
    assert record.requirement_coverage == 100
    assert record.traceability_reference_count == 2
    assert "does not establish" in record.interpretation_limit


def test_all_four_approaches_execute():
    runner = MeasuredBenchmarkRunner(client(), "mock", "mock-governed-v1")
    records = [
        runner.run(scenario(), approach)
        for approach in [
            "direct_prompt",
            "structured_prompt",
            "simple_chain",
            "intent_compilation",
        ]
    ]
    assert [record.calls for record in records] == [1, 1, 3, 6]
    assert all(record.schema_valid for record in records)
    assert all(not record.errors for record in records)
