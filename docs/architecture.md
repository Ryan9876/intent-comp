# Reference Architecture

## Purpose

The reference implementation proves the methodology's control plane. It deliberately does not attempt autonomous reasoning, multi-agent collaboration, or external provider execution.

## Components

1. **Triage gate** selects direct, minimum, or advanced operating mode.
2. **Typed artifacts** preserve objective, evidence, design, plan, contract, execution, verification, and learning.
3. **State machine** prevents invalid lifecycle transitions.
4. **Validators** enforce stage-specific invariants.
5. **Workflow controller** enforces ordering and upstream traceability.
6. **Executor adapters** perform bounded approved actions.
7. **Verifier adapters** produce evidence-backed completion status.
8. **JSON store and audit log** preserve state and trajectory.
9. **Benchmark harness** compares approaches using shared measures.

## Trust boundaries

- Artifact content may be AI-generated and remains provisional until reviewed.
- The state machine and validators are deterministic.
- The executor cannot grant itself authority.
- The safe demo executor is restricted to a configured workspace.
- Verification is separate from execution.
- Audit events are append-only in this reference implementation.

## Known limitations

- JSON persistence is not transactional or multi-user.
- No identity provider, RBAC service, signed approvals, or secrets manager.
- No model gateway or retrieval integration.
- No external tool adapters.
- No cryptographic audit integrity.
- No workflow resumption constructor from persisted state.
- Benchmark demo data is synthetic.

These are intentional boundaries for v0.1.0, not claims of production readiness.
