# Controlled Benchmark Protocol

## Objective

Compare direct prompting, a structured single prompt, a simple three-call chain, and the six-call Intent Compilation workflow using the same scenarios and model configuration.

## Controls

- Randomized approach order within each scenario/repeat block.
- Stable scenario IDs and fixed requirements.
- Provider, model, and policy held constant within a study.
- Approach identity removed from blind review packets.
- Blind-ID mapping stored separately from review packets.
- At least two independent reviews per output before drawing quality conclusions.
- Exact token usage captured from provider responses when available.
- Pricing loaded from an external dated configuration; prices are not hard-coded.
- Complete run and LLM audit records retained.

## Review rubric

Reviewers score each output from 1 (poor) to 5 (excellent) on:

1. Outcome quality
2. Completeness
3. Factuality
4. Actionability
5. Traceability
6. Verification quality

Reviewers also record critical errors, strengths, and confidence. Reviewers must not see the prompt approach, call count, model reasoning, or cost before scoring.

## Interpretation boundaries

- Schema validity and requirement matching are process metrics, not outcome quality.
- Randomization reduces order bias but does not remove scenario selection bias.
- Mock runs validate software plumbing only.
- A single model, reviewer population, or domain cannot establish universal superiority.
- Cost and latency must be reported alongside quality.
- Stage-level claims require enough paired reviewed blocks to support them.

## Live execution prerequisites

- An approved provider/model and current pricing source.
- `OPENAI_API_KEY` supplied through the environment for the OpenAI adapter.
- Explicit `--allow-network` flag.
- Public or approved internal benchmark data only.
- A fixed spend limit and isolated output directory.
