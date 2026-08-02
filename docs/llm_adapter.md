# Governed LLM Adapter

## Objective

Connect language-model reasoning to the deterministic control plane without allowing the model to become the authority, policy engine, execution engine, or source of completion truth.

## Control sequence

1. Build a typed `LLMRequest`.
2. Resolve provider and model against an allowlist.
3. Check data classification and network policy.
4. Check call, input, output, and optional cost budgets.
5. Wrap user material as untrusted input.
6. Request a JSON-schema-constrained response.
7. Parse and validate the response into a Pydantic model.
8. Store only hashes, metadata, usage, and status in the LLM audit log by default.
9. Convert validated output into a provisional methodology artifact.
10. Require the normal review/approval workflow before execution.

## Security properties

- API credentials are read from environment variables and are not persisted.
- Network access is disabled by policy unless explicitly enabled.
- Providers and models are allowlisted per client.
- Restricted data is rejected unless explicitly permitted.
- Raw prompt content is not included in the default audit record.
- Request and output hashes provide correlation without retaining content.
- Embedded instructions in source material are treated as untrusted data.
- Structured output is validated again locally even when the provider supports schema-constrained generation.
- The adapter has no tool-execution capability.

## OpenAI Responses adapter

The optional adapter sends requests to the Responses API and uses `text.format` with a strict JSON schema. It retries only transient HTTP/network failures and does not retry validation or authorization failures.

A live request requires all of:

- provider `openai`
- an explicitly approved model
- `network_access=true`
- `OPENAI_API_KEY` in the environment
- a permitted data classification
- remaining budget

## Remaining production work

- Secret-manager integration and key rotation
- Provider project separation for development/staging/production
- Token-accurate preflight budgets
- Model-specific pricing configuration
- Data-retention and residency policy enforcement
- Circuit breaker and distributed rate limiting
- Provider health monitoring
- Independent content safety and policy checks where required
- Human approval integration
- Encrypted audit storage and retention controls
