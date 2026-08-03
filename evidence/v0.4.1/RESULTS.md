# Intent Compiler v0.4.1 Reviewed Live-Study Results

## Evidence identity

- Study: `study-controlled-v1`
- GitHub Actions run: `30737052302`
- Source code commit tested: `c7e8f8f1615b49be36eed001e62de0613b0afc69`
- Model profile: GPT-5.6 Terra (`gpt-5.6-terra`)
- Scheduled and completed outputs: 24 of 24
- Independent blind reviews: 48, two per output
- Execution errors: 0
- Exact recorded study cost: $1.97318
- Spend ceiling: $5.00
- Publication guard after review: passed

## Observed results

| Approach | Mean blind-review score | Mean cost/output | Mean latency | Calls/output |
|---|---:|---:|---:|---:|
| Structured Prompt | **4.8889** | $0.02593 | 18.47 s | 1 |
| Simple Chain | 4.8611 | $0.07532 | 37.06 s | 3 |
| Intent Compilation | 4.7917 | $0.20599 | 90.57 s | 6 |
| Direct Prompt | 4.7083 | $0.02163 | 15.32 s | 1 |

Structured Prompt produced the highest observed mean blind-review score and the best observed quality-to-cost tradeoff in this study. Intent Compilation produced the strongest traceability result, but it did not have the highest overall quality score and was materially more expensive and slower.

Two outputs received substantive critical-error flags: one Direct Prompt leadership output and one Intent Compilation incident-response output.

## Interpretation boundary

These results are descriptive evidence for this controlled sample. They do not establish universal or statistically significant methodology superiority because the study used six scenarios, one model profile, one repeat per scenario, and three reviewers. The repository publication guard confirms completeness and policy compliance; it is not a hypothesis-significance test.

## Evidence files

- `combined-independent-reviews.csv`: normalized review table.
- `study-summary-after-review.json`: approach summaries, bootstrap intervals, and paired win rates.
- `publication-check-after-review.json`: passing post-review publication guard.
- `review-normalization-notes.txt`: documented normalization of literal `None` entries.
- `restricted/private-blind-mapping.json`: private unblinding map, retained only in this private repository.
- `restricted/run-records-audit-summary.json`: compact per-output execution, usage, and cost record.
- `restricted/llm-audit-digest-part*.jsonl`: per-call audit metadata and content hashes without prompt content.
- `restricted/private-controls-integrity.json`: hashes of the original private-control artifact and its files.
- `SHA256SUMS`: checksums for all retained evidence files.

The original binary workflow artifacts and Excel report remain available in the completed-run package, while the repository retains the machine-readable review, execution, cost, mapping, and audit evidence needed to reproduce and verify the reported findings.
