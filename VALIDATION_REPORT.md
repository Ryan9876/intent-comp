# Intent Compiler v0.4.1 Validation Report

## Scope

Validation of the v0.4.1 live-study reliability repair and the fresh controlled live benchmark executed from source commit `c7e8f8f1615b49be36eed001e62de0613b0afc69`.

## Reliability controls validated

- Provider response status and usage are recorded before schema validation.
- Incomplete and invalid structured responses are audited distinctly.
- One bounded structured-output retry is supported.
- Usage and cost completeness are tracked per execution.
- Failed records can be retried only when historical usage and cost are complete.
- Known prior attempt cost is preserved across retry replacement.
- Reviewer packets are withheld until all outputs are valid.
- Publication reports identify lower-bound cost when usage is incomplete.
- Hidden audit files are included in private GitHub Actions artifacts.

## Automated validation

- 34 automated tests passed for the v0.4.1 repair before the live study.
- Regression coverage includes incomplete provider responses, structured retry, preserved usage and audit data, blocked legacy resume, failed-output retry, and lower-bound publication accounting.

## Fresh live-study execution

GitHub Actions run `30737052302` completed successfully:

- 24 of 24 scheduled outputs were valid.
- 0 execution errors occurred.
- 0 structured-output failures remained.
- 0 retries were required.
- 171,680 input tokens and 102,932 output tokens were recorded.
- 274,612 total tokens were recorded.
- Exact study cost was $1.97318, below the $5.00 ceiling.
- Usage and cost evidence was complete for every record.

## Independent review validation

- 48 independent blind reviews were completed.
- Every output received exactly two assigned reviews.
- Reviewer IDs and blind-output assignments reconciled exactly to the generated assignment record.
- Literal none-like critical-error entries were normalized as no error, consistent with reviewer instructions.
- Two substantive critical-error findings remained in the final record.

## Publication validation

The post-review publication guard passed:

- all expected live records were present;
- exact usage and cost were complete;
- no execution errors were present;
- total cost was within policy;
- every output had the required independent reviews.

Comparative outcome-quality reporting is therefore permitted for this study. The guard does not establish statistical significance or universal methodology superiority.

## Evidence retention

The final reviewed evidence, manifest, checksums, reviewer-safe archive, and restricted audit archive are retained under [`evidence/v0.4.1/`](evidence/v0.4.1/). The source code under test remains bound to commit `c7e8f8f1615b49be36eed001e62de0613b0afc69`; the evidence closeout commit and merge history provide the immutable repository identity for the retained package.

## Remaining boundary

No further work is required to complete this benchmark. A larger multi-model, multi-repeat replication would increase generalizability but is a separate study rather than a v0.4.1 completion requirement.
