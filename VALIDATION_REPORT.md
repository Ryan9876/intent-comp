# Intent Compiler v0.4.0 Validation Report

## Result

**PASS WITH LIVE-RUN AND HUMAN-REVIEW LIMITATIONS**

## Repository validation

- The complete source tree is committed to `agent/publish-intent-compiler-v0.4.0`.
- GitHub Actions installed the package and passed all 30 automated tests on Python 3.11, 3.12, and 3.13.
- The repository contains no API key value or private-key material.
- Generated builds, caches, live-study records, and private blind mappings are excluded from source control.

## GitHub live-benchmark controls

The draft branch now includes `.github/workflows/live-benchmark.yml` with the following controls:

- manual `workflow_dispatch` only;
- separate no-content preflight and live execution jobs;
- exact `RUN-LIVE-STUDY` confirmation for execution;
- requested spend may lower but cannot exceed the repository policy limit;
- single-study concurrency;
- read-only repository permissions;
- protected `live-benchmark` environment for the execution job;
- reviewer-safe and private-control artifacts uploaded separately;
- publication guard expected to reject comparative quality claims before independent review.

## Model profile

The approved GPT-5.6 Terra profile was corrected to the official rates verified on August 2, 2026:

- input: $2.50 per million tokens;
- cached input: $0.25 per million tokens;
- output: $15.00 per million tokens.

The profile must be reverified against official sources before each live study because model availability and pricing can change.

## Not executed

No live OpenAI API request was made.

The following remain externally required:

1. Add `OPENAI_API_KEY` as a GitHub Actions repository secret.
2. Create a protected GitHub environment named `live-benchmark` and configure the required reviewer or approval policy.
3. Merge the draft pull request so the manual workflow is available from the default branch.
4. Run preflight and inspect its artifact before authorizing execution.
5. Complete independent blinded reviews before interpreting comparative quality.

## Evidence boundary

A successful live run would establish only that the selected model completed the configured scenarios under the recorded workflow and budget. Methodology superiority cannot be claimed unless the controlled study is complete, usage and costs are exact, independent blinded reviews are complete, and the publication guard passes. Any conclusion remains limited to the tested scenarios, model, prompts, policy, reviewers, and study period.
