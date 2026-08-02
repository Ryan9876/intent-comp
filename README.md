# Intent Compiler v0.4.0

A governed reference implementation for Intent Compilation with a controlled live-study release candidate.

## v0.4 highlights

- approved, dated live-model and pricing profiles;
- no-content credential/network/cost preflight;
- hard study spend limit and run reservation;
- resumable blinded study execution;
- balanced independent reviewer assignment;
- publication guards preventing unsupported quality claims.

See `docs/live_study_release_candidate.md` and `VALIDATION_REPORT.md`.


A reference implementation of the Intent Compilation Methodology: a finite, artifact-based workflow that transforms ambiguous objectives into governed, verifiable outcomes.

## What v0.3 adds

- Randomized, balanced benchmark schedules
- Blinded review packets
- Separate private approach mappings
- Review templates and validation
- Exact provider token capture when available
- Externally supplied dated pricing
- Statistical summaries and paired comparison plumbing
- Six controlled scenarios spanning software, networks, leadership, research, governance, and incident response

## Important evidence boundary

A mock run proves only that orchestration, randomization, blinding, storage, and analysis work. A live model run still does not establish superiority until outputs receive independent blind review.

## Quick validation

```bash
python -m pytest
python -m intent_compiler.cli benchmark-study-run \
  --provider mock \
  --model mock-governed-v1 \
  --config examples/study_config.json \
  --scenarios examples/controlled_benchmark_scenarios.json \
  --output-dir validation/mock-controlled-study
```

## Live controlled benchmark

Live use requires an approved model, current pricing configuration, an environment-provided `OPENAI_API_KEY`, and explicit network authorization.

```bash
export OPENAI_API_KEY='...'
python -m intent_compiler.cli benchmark-study-run \
  --provider openai \
  --model APPROVED_MODEL \
  --allow-network \
  --pricing pricing.current.json \
  --config examples/study_config.json \
  --scenarios examples/controlled_benchmark_scenarios.json \
  --output-dir controlled-study-live
```

Do not commit credentials, prompt content, or the private blind mapping to a reviewer-accessible location.

See `docs/controlled_benchmark.md` for the protocol.
