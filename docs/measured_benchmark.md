# Measured Benchmark Protocol

## Purpose

Compare four prompting approaches without fabricating quality results:

1. Direct prompt
2. Structured single prompt
3. Simple three-call chain
4. Six-call Intent Compilation workflow

## What the runner measures automatically

- provider and model
- mock versus live provider
- actual number of model calls
- wall-clock latency
- input and output characters
- schema validity
- exact requirement coverage
- traceability-reference count
- errors
- final structured output

## What it does not establish automatically

- correctness of the proposed solution
- domain quality
- factual accuracy beyond deterministic checks
- usefulness to a real user
- execution success in an external system
- superiority of one methodology

Those require blind human review, independent domain validation, tool-based verification, or a trusted reference answer.

## Mock runs

Mock runs are **integration benchmarks**. They prove that each workflow path executes, validates schemas, records telemetry, and preserves traceability. They must not be presented as evidence that Intent Compilation produces better answers.

## Live runs

Live runs should use:

- the same model and provider settings across approaches
- randomized task order
- multiple repetitions
- fixed scenario and rubric versions
- blind reviewers where practical
- retained prompts, artifacts, outputs, latency, token usage, and cost
- explicit failure and refusal handling

## Recommended scoring extension

Add a separate reviewer record containing:

- outcome quality (0–100)
- factual error count and severity
- requirement coverage confirmation
- rework minutes
- verification burden
- confidence calibration
- reviewer identity or anonymized ID
- rubric version

Do not let the model that produced the answer be the only judge of answer quality.
