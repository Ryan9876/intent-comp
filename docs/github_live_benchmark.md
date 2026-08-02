# Running the Live Benchmark in GitHub Actions

This repository includes a manual GitHub Actions workflow at `.github/workflows/live-benchmark.yml`.

The workflow is intentionally unavailable to automatic push or pull-request events. It can run only through `workflow_dispatch` after the workflow is present on the default branch.

## Safety model

The workflow separates the operation into two jobs:

1. **Preflight** performs credential, network, schedule, model-profile, and budget validation without sending benchmark content.
2. **Execution** runs only when preflight passes, the operator enters the exact confirmation phrase, and the `live-benchmark` GitHub environment permits the job to proceed.

Additional controls include:

- repository policy remains the maximum permitted spend;
- the workflow input can lower, but cannot raise, that limit;
- concurrent live studies are disabled;
- repository contents are read-only during the study;
- execution artifacts are retained for 14 days;
- reviewer-safe outputs are separated from the private approach mapping;
- the publication guard is expected to block quality claims until independent blinded reviews are imported.

## Required repository setup

Complete these steps after the draft pull request is reviewed and merged.

### 1. Add the API key as a GitHub Actions secret

Open:

`Settings -> Secrets and variables -> Actions -> New repository secret`

Create:

- Name: `OPENAI_API_KEY`
- Value: an API project key created specifically for this benchmark

Do not place the key in source files, workflow inputs, issues, pull requests, or action logs.

### 2. Create the protected environment

Open:

`Settings -> Environments -> New environment`

Create an environment named exactly:

`live-benchmark`

Recommended protection settings:

- require at least one reviewer;
- prevent self-review where available;
- limit deployment branches to `main`;
- use a short wait timer if an additional review window is useful.

The preflight job does not require environment approval. The execution job does.

### 3. Verify the model profile and pricing

The current approved profile is:

`examples/openai-gpt-5.6-terra-profile.json`

Before every live study, verify:

- the API model ID is still available to the project;
- the pricing effective date is current;
- input, cached-input, and output rates match official OpenAI sources;
- the configured repository spend limit is still acceptable.

The checked-in profile was verified on August 2, 2026. Pricing can change, so the profile must not be treated as permanently current.

## Running preflight

1. Open the repository's **Actions** tab.
2. Select **Live benchmark**.
3. Choose **Run workflow**.
4. Select:
   - Mode: `preflight`
   - Maximum spend: no more than the repository policy limit
5. Run the workflow.
6. Download the `live-benchmark-preflight` artifact.
7. Inspect `preflight.json`.

A ready result contains:

```json
{
  "credential_configured": true,
  "network_allowed": true,
  "ready_to_run": true,
  "blockers": []
}
```

Preflight reports readiness only. It sends no benchmark content and incurs no model-usage cost.

## Running the controlled study

Run the workflow again with:

- Mode: `run`
- Confirmation: `RUN-LIVE-STUDY`
- Maximum spend: an amount at or below the checked-in repository policy limit

The preflight must pass again. GitHub then pauses the execution job for approval in the `live-benchmark` environment.

After approval, the study runs through the OpenAI Responses API using the approved model profile and produces two artifact groups.

### Reviewer-safe artifact

`live-benchmark-reviewer-packet`

Contains:

- blinded outputs;
- review CSV template;
- balanced reviewer assignments;
- preflight report.

This artifact does not contain the private approach mapping.

### Private control artifact

`live-benchmark-private-controls`

Contains:

- run records and measured usage;
- private blind mapping;
- resume result;
- pre-review publication-guard result;
- hash-only LLM audit records;
- runtime policy used for the run.

Do not distribute the private mapping to reviewers before review completion.

## Expected publication status after execution

The workflow deliberately runs the publication guard before reviews are available. The guard must reject quality or superiority claims at that point.

A study can support comparative quality claims only after:

- all scheduled live outputs are complete;
- exact token and cost usage is available;
- no disqualifying execution errors remain;
- the spend limit was respected;
- every output has the required number of independent blinded reviews;
- the final publication guard passes.

Even a passing publication guard does not automatically prove universal methodology superiority. Conclusions must remain limited to the tested scenarios, model, configuration, reviewers, and study period.

## Failure handling

- **Missing key:** preflight reports `OPENAI_API_KEY is not configured`.
- **Invalid key or model access:** execution stops with the provider error; partial records are uploaded where available.
- **Requested spend exceeds policy:** the workflow stops before preflight.
- **Reserved study cost exceeds the requested ceiling:** preflight blocks execution.
- **Interrupted study:** use the CLI resume support with the downloaded private run records. The GitHub workflow currently starts a new run and does not automatically import prior artifacts.
- **Publication guard unexpectedly passes before review:** the workflow fails because that indicates a control defect.

## Current limitation

GitHub does not allow ChatGPT to create the `OPENAI_API_KEY` secret or configure required environment reviewers through the connected repository interface used for this project. Those two settings must be completed in the GitHub user interface by a repository administrator.
