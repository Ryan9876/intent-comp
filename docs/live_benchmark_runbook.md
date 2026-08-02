# Live Benchmark Runbook

## Decision boundary

A live run is authorized only when all of the following are true:

- The model is explicitly approved.
- The benchmark scenarios contain only public or approved internal data.
- `OPENAI_API_KEY` is supplied through the environment.
- Network access is explicitly enabled with `--allow-network`.
- A current dated pricing configuration is supplied.
- A maximum spend has been accepted.
- Output and audit directories are isolated.
- Reviewers do not receive the private blind mapping.

## Preparation

1. Copy `examples/pricing.example.json` to a private dated pricing file.
2. Enter current official input and output token prices for the approved model.
3. Increase `repeats_per_scenario` only after a small smoke run succeeds.
4. Record the model ID, methodology version, scenario version, and study seed.
5. Ensure that the output directory is empty.

## Execute

```bash
export OPENAI_API_KEY='...'
intent-compiler benchmark-study-run \
  --provider openai \
  --model APPROVED_MODEL \
  --allow-network \
  --pricing pricing.current.json \
  --config examples/study_config.json \
  --scenarios examples/controlled_benchmark_scenarios.json \
  --audit-dir .intent-compiler-live-audit \
  --output-dir controlled-study-live
```

## Blind review

- Give reviewers `blind-review-packets.jsonl` and `blind-review-template.csv`.
- Do not give them `schedule.jsonl`, `run-records.jsonl`, LLM audit records, or `private-blind-mapping.json`.
- Use at least two independent reviewers per output.
- Resolve missing scores before analysis; do not impute reviewer scores.

## Import and summarize

```bash
intent-compiler benchmark-review-import \
  --input completed-blind-review.csv \
  --output controlled-study-live/reviews.jsonl

intent-compiler benchmark-study-summarize \
  --config examples/study_config.json \
  --records controlled-study-live/run-records.jsonl \
  --mapping controlled-study-live/private-blind-mapping.json \
  --reviews controlled-study-live/reviews.jsonl \
  --output controlled-study-live/final-summary.json
```

## Interpretation

Do not claim that an approach is superior from schema validity, requirement coverage, or mock results alone. Review quality, critical errors, cost, latency, model configuration, scenario mix, and confidence intervals together.
