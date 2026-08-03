# Intent Compiler v0.4.1

A governed reference implementation for Intent Compilation: a finite, artifact-based workflow that transforms ambiguous objectives into traceable execution and verifiable outcomes.

## v0.4.1 status

The v0.4.1 reliability repair and fresh controlled live study are complete. GitHub Actions run `30737052302` executed all 24 scheduled outputs from source commit `c7e8f8f1615b49be36eed001e62de0613b0afc69`, recorded exact usage and cost, and produced a complete reviewer packet. Three independent reviewers completed 48 blind reviews, satisfying the required two reviews per output. The post-review publication guard passed.

Reviewed evidence is retained under [`evidence/v0.4.1/`](evidence/v0.4.1/). See [`RESULTS.md`](evidence/v0.4.1/RESULTS.md) for the findings and interpretation limits.

## Observed benchmark result

| Approach | Mean blind-review score | Mean cost/output | Mean latency | Calls/output |
|---|---:|---:|---:|---:|
| Structured Prompt | **4.8889** | $0.02593 | 18.47 s | 1 |
| Simple Chain | 4.8611 | $0.07532 | 37.06 s | 3 |
| Intent Compilation | 4.7917 | $0.20599 | 90.57 s | 6 |
| Direct Prompt | 4.7083 | $0.02163 | 15.32 s | 1 |

Structured Prompt produced the highest observed mean score and the best observed quality-to-cost tradeoff in this sample. Intent Compilation produced the strongest traceability result, but it did not have the highest overall quality score.

These are descriptive controlled-sample findings, not proof of universal or statistically significant superiority.

## v0.4 controls

- approved, dated live-model and pricing profiles;
- no-content credential, network, schedule, and cost preflight;
- hard study spend limits and conservative per-run reservation;
- resumable blinded study execution with exact historical accounting;
- balanced independent reviewer assignment;
- publication guards preventing unsupported quality claims;
- separate reviewer-safe and restricted audit evidence.

## Local validation

```bash
python -m pip install -e '.[dev]'
python -m pytest
```

## Mock controlled benchmark

```bash
python -m intent_compiler.cli benchmark-study-run \
  --provider mock \
  --model mock-governed-v1 \
  --config examples/study_config.json \
  --scenarios examples/controlled_benchmark_scenarios.json \
  --output-dir validation/mock-controlled-study
```

## Live controlled benchmark

Live use requires an approved model, current pricing configuration, an environment-provided `OPENAI_API_KEY`, explicit network authorization, an exact confirmation token, and a spend ceiling within policy.

See:

- [`docs/controlled_benchmark.md`](docs/controlled_benchmark.md)
- [`docs/live_study_release_candidate.md`](docs/live_study_release_candidate.md)
- [`VALIDATION_REPORT.md`](VALIDATION_REPORT.md)
- [`evidence/v0.4.1/RESULTS.md`](evidence/v0.4.1/RESULTS.md)

Do not expose credentials or the restricted private audit archive to reviewers.
