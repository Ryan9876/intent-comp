# Intent Compiler v0.4.0 Validation Report

## Result

**PASS WITH LIVE-RUN AND HUMAN-REVIEW LIMITATIONS**

The package is a live-study release candidate. Its control and packaging paths were tested locally. No live OpenAI request was sent because `OPENAI_API_KEY` is not configured, and no independent human reviews were performed.

## Automated validation

- 30 automated tests passed.
- Python source compilation passed.
- Credential-free live-study preflight correctly returned blocked status.
- Preflight recorded `content_sent: false`.
- The selected 24-run study fits the $5.00 study cap using a $0.20 conservative reserve per run ($4.80 reserved).
- Reviewer assignment produced 48 assignments: two reviewers for each of 24 blinded outputs.
- Reviewer load was exactly balanced across three reviewer IDs (16 assignments each).
- Publication guard correctly rejected the mock study because it was not live, lacked exact token/cost usage, and had no independent reviews.
- The pre-existing mock controlled-study records remained complete: 24 runs with no execution errors.

## Approved example model profile

- Provider: OpenAI
- Model: GPT-5.6 Terra
- API model ID: `gpt-5.6-terra`
- Price effective date recorded: 2026-08-02
- Input: $2.00 per 1M tokens
- Cached input: $0.20 per 1M tokens
- Output: $12.00 per 1M tokens

The model and pricing values were taken from official OpenAI pages on 2026-08-02. They must be rechecked before a live run.

## Live boundary

Not performed:

- no live API calls;
- no live token or cost records;
- no independent blind reviews;
- no quality comparison;
- no methodology-superiority conclusion.

The actual preflight is blocked by two conditions:

1. `OPENAI_API_KEY` is not configured.
2. Network access was not explicitly allowed.

## Publication boundary

The package prevents a quality claim until all scheduled records are live and complete, exact token/cost data are present, the spend cap is respected, execution errors are zero, and every output has at least two independent blind reviews.
