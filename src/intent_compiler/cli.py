from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .artifact_generation import LLMArtifactGenerator
from .benchmark import BenchmarkHarness, BenchmarkMetrics, BenchmarkRun
from .benchmark_execution import MeasuredBenchmarkRunner, load_scenarios, write_records
from .benchmark_study import (
    BlindReviewPacket,
    PricingConfig,
    ReviewRecord,
    StudyConfig,
    StudyRunRecord,
    build_schedule,
    create_blind_packets,
    import_reviews_csv,
    read_jsonl,
    run_study,
    summarize_study,
    write_jsonl,
    write_mapping,
    write_review_template,
)
from .demo import run_demo
from .llm_adapters import GovernedLLMClient
from .llm_models import LLMBudget, LLMPolicy
from .models import TriageAssessment
from .provider_factory import create_provider
from .storage import JsonStore
from .live_study import (
    ApprovedModelProfile,
    LiveStudyPolicy,
    assign_reviewers,
    preflight_live_study,
    publication_guard,
    run_resumable_study,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="intent-compiler")
    sub = parser.add_subparsers(dest="command", required=True)

    triage = sub.add_parser("triage", help="Score a task through the methodology triage gate")
    for field in ["complexity", "consequence", "ambiguity", "reuse", "evidence_burden"]:
        triage.add_argument(f"--{field.replace('_', '-')}", type=int, choices=[0, 1, 2], required=True)
    triage.add_argument("--override", action="store_true")
    triage.add_argument("--rationale", required=True)

    demo = sub.add_parser("demo", help="Execute a bounded local reference workflow")
    demo.add_argument("--workspace", default="./intent-compiler-demo")

    benchmark = sub.add_parser("benchmark-demo", help="Write a legacy illustrative synthetic summary")
    benchmark.add_argument("--output", default="./benchmark-summary.json")

    check = sub.add_parser("llm-check", help="Inspect LLM adapter readiness without sending content")
    check.add_argument("--provider", choices=["mock", "openai"], default="mock")
    check.add_argument("--model", default="mock-governed-v1")
    check.add_argument("--allow-network", action="store_true")

    objective = sub.add_parser("generate-objective", help="Generate and validate an objective artifact")
    objective.add_argument("--provider", choices=["mock", "openai"], default="mock")
    objective.add_argument("--model", default="mock-governed-v1")
    source = objective.add_mutually_exclusive_group(required=True)
    source.add_argument("--text")
    source.add_argument("--input-file")
    objective.add_argument("--output", required=True)
    objective.add_argument("--audit-dir", default="./.intent-compiler-llm")
    objective.add_argument("--allow-network", action="store_true")

    measured = sub.add_parser("benchmark-run", help="Run measured benchmark plumbing across four approaches")
    measured.add_argument("--provider", choices=["mock", "openai"], default="mock")
    measured.add_argument("--model", default="mock-governed-v1")
    measured.add_argument("--scenarios", default="./examples/benchmark_scenarios.json")
    measured.add_argument("--output", default="./benchmark-runs.jsonl")
    measured.add_argument("--audit-dir", default="./.intent-compiler-benchmark")
    measured.add_argument("--allow-network", action="store_true")

    study = sub.add_parser("benchmark-study-run", help="Run a randomized controlled benchmark study")
    study.add_argument("--provider", choices=["mock", "openai"], default="mock")
    study.add_argument("--model", default="mock-governed-v1")
    study.add_argument("--config", default="./examples/study_config.json")
    study.add_argument("--scenarios", default="./examples/controlled_benchmark_scenarios.json")
    study.add_argument("--output-dir", default="./controlled-benchmark")
    study.add_argument("--pricing")
    study.add_argument("--audit-dir", default="./.intent-compiler-controlled-benchmark")
    study.add_argument("--allow-network", action="store_true")

    review = sub.add_parser("benchmark-review-import", help="Validate and import blinded review CSV")
    review.add_argument("--input", required=True)
    review.add_argument("--output", required=True)

    summary = sub.add_parser("benchmark-study-summarize", help="Summarize controlled runs and blind reviews")
    summary.add_argument("--config", required=True)
    summary.add_argument("--records", required=True)
    summary.add_argument("--mapping", required=True)
    summary.add_argument("--reviews")
    summary.add_argument("--output", required=True)

    live_preflight = sub.add_parser("live-study-preflight", help="Validate live-study readiness without sending content")
    live_preflight.add_argument("--config", default="./examples/study_config.json")
    live_preflight.add_argument("--scenarios", default="./examples/controlled_benchmark_scenarios.json")
    live_preflight.add_argument("--profile", default="./examples/openai-gpt-5.6-terra-profile.json")
    live_preflight.add_argument("--policy", default="./examples/live-study-policy.json")
    live_preflight.add_argument("--existing-records")
    live_preflight.add_argument("--allow-network", action="store_true")
    live_preflight.add_argument("--output", required=True)

    live_run = sub.add_parser("live-study-run", help="Run or resume the approved live controlled study")
    live_run.add_argument("--config", default="./examples/study_config.json")
    live_run.add_argument("--scenarios", default="./examples/controlled_benchmark_scenarios.json")
    live_run.add_argument("--profile", default="./examples/openai-gpt-5.6-terra-profile.json")
    live_run.add_argument("--policy", default="./examples/live-study-policy.json")
    live_run.add_argument("--existing-records")
    live_run.add_argument("--output-dir", required=True)
    live_run.add_argument("--audit-dir", default="./.intent-compiler-live-study")
    live_run.add_argument("--allow-network", action="store_true")

    assignments = sub.add_parser("live-study-assign-reviewers", help="Create balanced blinded reviewer assignments")
    assignments.add_argument("--study-id", required=True)
    assignments.add_argument("--packets", required=True)
    assignments.add_argument("--policy", default="./examples/live-study-policy.json")
    assignments.add_argument("--output", required=True)

    publish = sub.add_parser("live-study-publication-check", help="Block unsupported quality or superiority claims")
    publish.add_argument("--config", required=True)
    publish.add_argument("--records", required=True)
    publish.add_argument("--reviews")
    publish.add_argument("--policy", default="./examples/live-study-policy.json")
    publish.add_argument("--scenarios")
    publish.add_argument("--output", required=True)
    return parser


def illustrative_benchmark() -> BenchmarkHarness:
    harness = BenchmarkHarness()
    rows = [
        ("direct_prompt", 70, 8, 68, 65, 22, 35, 18, 8, 0.08, 15),
        ("structured_prompt", 78, 5, 79, 74, 17, 55, 25, 13, 0.14, 13),
        ("simple_chain", 84, 4, 87, 82, 12, 72, 34, 26, 0.32, 11),
        ("intent_compilation", 91, 2, 95, 91, 7, 94, 48, 44, 0.61, 8),
    ]
    for row in rows:
        approach, quality, error, coverage, success, rework, trace, effort, latency, cost, verification = row
        harness.add(
            BenchmarkRun(
                scenario_id="illustrative-network-change",
                domain="network_operations",
                approach=approach,
                metrics=BenchmarkMetrics(
                    outcome_quality=quality,
                    factual_error_rate=error,
                    requirement_coverage=coverage,
                    execution_success=success,
                    rework_minutes=rework,
                    traceability=trace,
                    human_effort_minutes=effort,
                    latency_seconds=latency,
                    cost_usd=cost,
                    verification_burden_minutes=verification,
                ),
                notes="Illustrative synthetic data only; replace with measured benchmark results.",
            )
        )
    return harness


def build_client(
    provider_name: str,
    model: str,
    allow_network: bool,
    store: JsonStore,
    max_calls: int,
) -> GovernedLLMClient:
    provider = create_provider(provider_name, model=model)
    policy = LLMPolicy(
        allowed_providers=[provider_name],
        allowed_models={provider_name: [model]},
        network_access=allow_network,
        permitted_data_classifications=["public", "internal"],
        require_structured_output=True,
        record_prompt_content=False,
        budget=LLMBudget(
            max_calls=max_calls,
            max_input_chars=2_000_000,
            max_output_chars=1_000_000,
        ),
    )
    return GovernedLLMClient(provider, policy, audit_sink=store.append_llm_audit)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "triage":
        assessment = TriageAssessment(
            complexity=args.complexity,
            consequence=args.consequence,
            ambiguity=args.ambiguity,
            reuse=args.reuse,
            evidence_burden=args.evidence_burden,
            high_consequence_override=args.override,
            rationale=args.rationale,
        )
        print(json.dumps({"score": assessment.score, "mode": assessment.mode}, indent=2))
        return 0
    if args.command == "demo":
        result = run_demo(Path(args.workspace))
        print(json.dumps(result, indent=2, default=str))
        return 0
    if args.command == "benchmark-demo":
        harness = illustrative_benchmark()
        output = harness.write_summary(args.output)
        print(json.dumps({"output": str(output), "warning": "illustrative synthetic data"}, indent=2))
        return 0
    if args.command == "llm-check":
        configured = args.provider == "mock" or bool(os.getenv("OPENAI_API_KEY"))
        print(
            json.dumps(
                {
                    "provider": args.provider,
                    "model": args.model,
                    "credential_configured": configured,
                    "network_allowed": args.allow_network,
                    "ready": configured and (args.provider == "mock" or args.allow_network),
                    "content_sent": False,
                },
                indent=2,
            )
        )
        return 0
    if args.command == "generate-objective":
        store = JsonStore(args.audit_dir)
        client = build_client(args.provider, args.model, args.allow_network, store, max_calls=2)
        raw = args.text if args.text is not None else Path(args.input_file).read_text(encoding="utf-8")
        generator = LLMArtifactGenerator(client, args.provider, args.model)
        artifact = generator.generate_objective(raw)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
        print(
            json.dumps(
                {
                    "output": str(output),
                    "artifact_id": artifact.artifact_id,
                    "provider": args.provider,
                    "audit": str(store.llm_audit_path),
                },
                indent=2,
            )
        )
        return 0
    if args.command == "benchmark-study-run":
        store = JsonStore(args.audit_dir)
        config = StudyConfig.model_validate_json(Path(args.config).read_text(encoding="utf-8"))
        scenarios = load_scenarios(args.scenarios)
        pricing = (
            PricingConfig.model_validate_json(Path(args.pricing).read_text(encoding="utf-8"))
            if args.pricing
            else None
        )
        max_calls = max(100, len(scenarios) * config.repeats_per_scenario * 30)
        client = build_client(args.provider, args.model, args.allow_network, store, max_calls=max_calls)
        runner = MeasuredBenchmarkRunner(client, args.provider, args.model)
        schedule, records = run_study(config, scenarios, runner, pricing=pricing)
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        packets, mapping = create_blind_packets(records, scenarios)
        write_jsonl(schedule, output_dir / "schedule.jsonl")
        write_jsonl(records, output_dir / "run-records.jsonl")
        write_jsonl(packets, output_dir / "blind-review-packets.jsonl")
        write_mapping(mapping, output_dir / "private-blind-mapping.json")
        write_review_template(config.study_id, packets, output_dir / "blind-review-template.csv")
        empty_summary = summarize_study(config, records, [], mapping)
        (output_dir / "summary-before-review.json").write_text(
            empty_summary.model_dump_json(indent=2), encoding="utf-8"
        )
        print(json.dumps({
            "study_id": config.study_id,
            "runs": len(records),
            "blind_packets": len(packets),
            "output_dir": str(output_dir),
            "provider_kind": "mock" if args.provider == "mock" else "live",
            "live_claim": args.provider != "mock",
            "review_conclusion_supported": False,
            "warning": "No comparative outcome-quality conclusion is supported until independent blind reviews are imported.",
        }, indent=2))
        return 0
    if args.command == "benchmark-review-import":
        reviews = import_reviews_csv(args.input)
        write_jsonl(reviews, args.output)
        print(json.dumps({"reviews": len(reviews), "output": args.output}, indent=2))
        return 0
    if args.command == "benchmark-study-summarize":
        config = StudyConfig.model_validate_json(Path(args.config).read_text(encoding="utf-8"))
        records = [StudyRunRecord.model_validate(item) for item in read_jsonl(args.records, StudyRunRecord)]
        mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
        reviews = (
            [ReviewRecord.model_validate(item) for item in read_jsonl(args.reviews, ReviewRecord)]
            if args.reviews
            else []
        )
        result = summarize_study(config, records, reviews, mapping)
        Path(args.output).write_text(result.model_dump_json(indent=2), encoding="utf-8")
        print(json.dumps({"output": args.output, "reviews": len(reviews)}, indent=2))
        return 0

    if args.command == "live-study-preflight":
        config = StudyConfig.model_validate_json(Path(args.config).read_text(encoding="utf-8"))
        scenarios = load_scenarios(args.scenarios)
        profile = ApprovedModelProfile.model_validate_json(Path(args.profile).read_text(encoding="utf-8"))
        policy = LiveStudyPolicy.model_validate_json(Path(args.policy).read_text(encoding="utf-8"))
        existing = (
            [StudyRunRecord.model_validate(item) for item in read_jsonl(args.existing_records, StudyRunRecord)]
            if args.existing_records
            else []
        )
        report = preflight_live_study(
            config, scenarios, args.scenarios, profile, policy,
            network_allowed=args.allow_network, existing_records=existing,
        )
        write_json(report, args.output)
        print(report.model_dump_json(indent=2))
        return 0 if report.ready_to_run else 2

    if args.command == "live-study-run":
        config = StudyConfig.model_validate_json(Path(args.config).read_text(encoding="utf-8"))
        scenarios = load_scenarios(args.scenarios)
        profile = ApprovedModelProfile.model_validate_json(Path(args.profile).read_text(encoding="utf-8"))
        policy = LiveStudyPolicy.model_validate_json(Path(args.policy).read_text(encoding="utf-8"))
        existing = (
            [StudyRunRecord.model_validate(item) for item in read_jsonl(args.existing_records, StudyRunRecord)]
            if args.existing_records
            else []
        )
        preflight = preflight_live_study(
            config, scenarios, args.scenarios, profile, policy,
            network_allowed=args.allow_network, existing_records=existing,
        )
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(preflight, output_dir / "preflight.json")
        if not preflight.ready_to_run:
            print(preflight.model_dump_json(indent=2))
            return 2
        store = JsonStore(args.audit_dir)
        max_calls = max(100, preflight.remaining_runs * 8)
        client = build_client(profile.provider, profile.api_model_id, True, store, max_calls=max_calls)
        runner = MeasuredBenchmarkRunner(client, profile.provider, profile.api_model_id)
        result = run_resumable_study(config, scenarios, runner, profile.pricing(), policy, existing)
        write_jsonl(result.records, output_dir / "run-records.jsonl")
        if result.review_packet_ready:
            packets, mapping = create_blind_packets(result.records, scenarios)
            write_jsonl(packets, output_dir / "blind-review-packets.jsonl")
            write_mapping(mapping, output_dir / "private-blind-mapping.json")
            write_review_template(config.study_id, packets, output_dir / "blind-review-template.csv")
        else:
            for stale_name in [
                "blind-review-packets.jsonl",
                "private-blind-mapping.json",
                "blind-review-template.csv",
                "reviewer-assignments.json",
            ]:
                stale = output_dir / stale_name
                if stale.exists():
                    stale.unlink()
        write_json(result, output_dir / "resume-result.json")
        print(result.model_dump_json(indent=2))
        return 0 if not result.stopped_for_budget else 3

    if args.command == "live-study-assign-reviewers":
        packets = list(read_jsonl(args.packets, BlindReviewPacket))
        policy = LiveStudyPolicy.model_validate_json(Path(args.policy).read_text(encoding="utf-8"))
        assigned = assign_reviewers(args.study_id, packets, policy)
        write_json(assigned, args.output)
        print(json.dumps({"assignments": len(assigned), "output": args.output}, indent=2))
        return 0

    if args.command == "live-study-publication-check":
        config = StudyConfig.model_validate_json(Path(args.config).read_text(encoding="utf-8"))
        records = [StudyRunRecord.model_validate(item) for item in read_jsonl(args.records, StudyRunRecord)]
        reviews = (
            [ReviewRecord.model_validate(item) for item in read_jsonl(args.reviews, ReviewRecord)]
            if args.reviews else []
        )
        policy = LiveStudyPolicy.model_validate_json(Path(args.policy).read_text(encoding="utf-8"))
        expected_scenarios = len(load_scenarios(args.scenarios)) if args.scenarios else None
        report = publication_guard(config, records, reviews, policy, expected_scenarios=expected_scenarios)
        write_json(report, args.output)
        print(report.model_dump_json(indent=2))
        return 0 if report.quality_claim_allowed else 4

    if args.command == "benchmark-run":
        store = JsonStore(args.audit_dir)
        scenarios = load_scenarios(args.scenarios)
        max_calls = max(40, len(scenarios) * 20)
        client = build_client(args.provider, args.model, args.allow_network, store, max_calls=max_calls)
        runner = MeasuredBenchmarkRunner(client, args.provider, args.model)
        approaches = ["direct_prompt", "structured_prompt", "simple_chain", "intent_compilation"]
        records = [runner.run(scenario, approach) for scenario in scenarios for approach in approaches]
        output = write_records(records, args.output)
        print(
            json.dumps(
                {
                    "output": str(output),
                    "records": len(records),
                    "provider_kind": "mock" if args.provider == "mock" else "live",
                    "audit": str(store.llm_audit_path),
                    "warning": (
                        "Mock runs validate integration only; they do not establish model-quality superiority."
                        if args.provider == "mock"
                        else "Outcome quality still requires blind human or independent domain review."
                    ),
                },
                indent=2,
            )
        )
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
