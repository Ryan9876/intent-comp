# Live Study Evidence Release — v0.4.1

Version 0.4.1 contains the controls and retained evidence for a complete live comparative study.

## Guarded execution controls

- approved model profile with dated pricing;
- hard total-study spend limit and conservative per-run reserve;
- credential and network preflight without sending content;
- resumable execution keyed by blinded output ID;
- exact usage and historical-cost accounting;
- balanced independent reviewer assignment;
- publication guards for incomplete, unreviewed, over-budget, error-containing, or usage-incomplete studies.

## Completed study

GitHub Actions run `30737052302` executed 24 outputs using GPT-5.6 Terra from source commit `c7e8f8f1615b49be36eed001e62de0613b0afc69`. The run completed with zero execution errors, complete token and cost evidence, and an exact recorded cost of $1.97318.

Three independent reviewers completed 48 blind reviews. Every output received two reviews. The post-review publication guard passed.

## Observed findings

Structured Prompt had the highest observed mean blind-review score at 4.8889/5 and the best observed quality-to-cost tradeoff. Simple Chain scored 4.8611, Intent Compilation scored 4.7917, and Direct Prompt scored 4.7083. Intent Compilation had the strongest traceability result, but was the slowest and most expensive approach.

## Publication boundary

The completed controls permit comparative reporting for this study. Claims must remain bounded to the tested sample. The study does not establish universal or statistically significant methodology superiority because it used six scenarios, one model, one repeat per scenario, and three reviewers.

## Retained evidence

The evidence package is stored under [`evidence/v0.4.1/`](../evidence/v0.4.1/), with reviewer-safe evidence separated from a restricted audit archive. Checksums and a machine-readable manifest are included.
