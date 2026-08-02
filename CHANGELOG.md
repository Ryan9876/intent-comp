# Changelog

## Unreleased

- Added a manual GitHub Actions workflow for guarded live benchmarking.
- Separated no-content preflight from protected live execution.
- Added exact run confirmation, concurrency control, spend-cap enforcement, and artifact separation.
- Added GitHub setup and operating instructions for repository secrets, protected environments, review packets, and private control records.
- Corrected the GPT-5.6 Terra profile to the official August 2, 2026 rates: $2.50 input, $0.25 cached input, and $15.00 output per million tokens.

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
