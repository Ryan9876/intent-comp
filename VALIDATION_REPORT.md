# Intent Compiler v0.4.1 Validation Report

## Scope

Focused reliability repair following the first controlled live study. No live API requests were made during this repair.

## Root cause addressed

The v0.4.0 OpenAI adapter parsed structured output before returning the provider response. Invalid or incomplete JSON therefore discarded the response usage and caused some failed records to report zero tokens and zero cost. Resumable execution also treated any existing blind output ID as complete, even when its output had failed validation.

## Implemented controls

- Provider response status and usage are recorded before schema validation.
- Incomplete and invalid structured responses are audited distinctly.
- One bounded structured-output retry is supported.
- Benchmark final calls use a larger explicit output-token ceiling.
- Usage completeness is tracked per execution instead of poisoning all later executions.
- Failed records can be retried only when historical usage and cost are complete.
- Known prior attempt cost is preserved across retry replacement.
- Reviewer packets are withheld until all outputs are valid.
- Publication reports identify lower-bound cost when usage is incomplete.
- Hidden audit files are included in private GitHub Actions artifacts.

## Automated validation

- 34 tests passed locally with `PYTHONPATH=src pytest -q`.
- Added regression coverage for incomplete provider responses, structured retry, preserved usage/audit data, blocked legacy resume, failed-output retry, and lower-bound publication accounting.

## Remaining boundary

The original v0.4.0 live run cannot be converted into an exact-cost study because its missing failed-response usage was never retained. A fresh controlled study is required for publishable exact usage and cost comparisons.
