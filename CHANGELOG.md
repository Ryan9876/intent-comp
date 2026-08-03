# Changelog

## 0.4.1 — Reviewed live-study evidence closeout

- Preserve provider response status, token usage, and audit evidence before structured-output validation.
- Detect incomplete responses and retry invalid structured output once with a bounded token increase.
- Prevent legacy records with incomplete historical billing evidence from being resumed as exact-cost studies.
- Withhold reviewer packets until every scheduled output is valid and usage-complete.
- Complete fresh controlled live-study run 30737052302 with 24 valid outputs, zero execution errors, and exact cost of $1.97318.
- Complete 48 independent blind reviews, providing two reviews for every output.
- Pass the post-review publication guard.
- Retain reviewed results, normalized reviews, study summary, publication record, manifest, checksums, restricted mapping, execution ledger, audit digests, effective policy, and original-artifact integrity hashes under `evidence/v0.4.1/`.
- Document Structured Prompt as the highest observed quality and quality-to-cost result while preserving sample-size and generalizability limits.

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
