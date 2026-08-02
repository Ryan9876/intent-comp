# Intent Compiler v0.4.0

A governed reference implementation for **Intent Compilation**: a finite, artifact-based workflow that transforms ambiguous objectives into traceable execution and verifiable outcomes.

## v0.4 highlights

- approved, dated live-model and pricing profiles;
- no-content credential, network, schedule, and cost preflight;
- hard study spend limits and per-run reservation;
- resumable blinded study execution;
- balanced independent reviewer assignment;
- publication guards preventing unsupported quality claims;
- manual GitHub Actions workflow for protected live benchmarking.

See:

- `docs/live_study_release_candidate.md`
- `docs/github_live_benchmark.md`
- `VALIDATION_REPORT.md`

## Evidence boundary

Mock runs prove only that orchestration, randomization, blinding, storage, and analysis work. A live-model run still does not establish methodology superiority until outputs receive independent blind review and the publication guard passes.

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

## Live benchmark through GitHub Actions

After this branch is merged into `main`:

1. Add `OPENAI_API_KEY` as a repository Actions secret.
2. Create a protected GitHub environment named `live-benchmark`.
3. Open **Actions -> Live benchmark**.
4. Run `preflight` first.
5. Review the preflight artifact.
6. Run `run` with the exact confirmation `RUN-LIVE-STUDY` and an approved spend ceiling.

The execution job requires the `live-benchmark` environment and is never triggered automatically by pushes or pull requests.

Detailed instructions are in `docs/github_live_benchmark.md`.

## Local live-study commands

Live use requires an approved model profile, current pricing, an environment-provided `OPENAI_API_KEY`, and explicit network authorization.

```bash
export OPENAI_API_KEY='...'

python -m intent_compiler.cli live-study-preflight \
  --config examples/study_config.json \
  --scenarios examples/controlled_benchmark_scenarios.json \
  --profile examples/openai-gpt-5.6-terra-profile.json \
  --policy examples/live-study-policy.json \
  --allow-network \
  --output validation/live-preflight.json

python -m intent_compiler.cli live-study-run \
  --config examples/study_config.json \
  --scenarios examples/controlled_benchmark_scenarios.json \
  --profile examples/openai-gpt-5.6-terra-profile.json \
  --policy examples/live-study-policy.json \
  --allow-network \
  --output-dir validation/live-study \
  --audit-dir .intent-compiler-live-study
```

Do not commit credentials, prompt content, generated private mappings, or live-study control artifacts.
