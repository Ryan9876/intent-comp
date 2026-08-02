from intent_compiler.benchmark import BenchmarkHarness, BenchmarkMetrics, BenchmarkRun


def metrics(quality):
    return BenchmarkMetrics(
        outcome_quality=quality,
        factual_error_rate=1,
        requirement_coverage=90,
        execution_success=90,
        rework_minutes=5,
        traceability=90,
        human_effort_minutes=20,
        latency_seconds=10,
        cost_usd=0.2,
        verification_burden_minutes=5,
    )


def test_benchmark_summary_averages_runs():
    harness = BenchmarkHarness()
    harness.add(BenchmarkRun(scenario_id="a", domain="test", approach="direct_prompt", metrics=metrics(60)))
    harness.add(BenchmarkRun(scenario_id="b", domain="test", approach="direct_prompt", metrics=metrics(80)))
    assert harness.summarize()["direct_prompt"]["outcome_quality"] == 70
