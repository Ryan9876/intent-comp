# Changelog

## 0.4.1 — Live-study reliability repair

- Preserve provider response status, token usage, and audit evidence before structured-output validation.
- Detect incomplete responses and retry invalid structured output once with a bounded token increase.
- Distinguish provider completion, schema validity, usage completeness, and execution errors.
- Prevent legacy records with incomplete historical billing evidence from being resumed as exact-cost studies.
- Retry failed outputs while preserving prior known attempt cost for v0.4.1-compatible records.
- Withhold reviewer packets until every scheduled output is valid and usage-complete.
- Mark incomplete study cost as a lower bound in the publication guard.
- Include hidden audit records in private GitHub Actions artifacts and support optional prior-run artifact input.

## 0.4.0 — 2026-08-02

- Added an approved live-model profile for GPT-5.6 Terra with dated official pricing.
- Added credential/network/cost preflight that sends no content.
- Added conservative hard-spend reservation and study run limits.
- Added resumable controlled-study execution keyed by blind output ID.
- Added balanced blinded reviewer assignment.
- Added publication guards blocking unsupported live-quality or methodology-superiority claims.
- Added live-study runbook and reviewer-assignment documentation.
- Expanded the automated suite from 25 to 30 tests.

## 0.3.0

- Added controlled randomized benchmark scheduling, blinded packets, review import, and statistical summaries.
