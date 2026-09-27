# Artifact model

## Artifact classes

Thesys manages several artifact classes:

- **Authoritative artifact:** a human-approved source of truth for its scope.
- **Proposal:** non-authoritative content produced by a human or agent before
  acceptance.
- **Evidence:** an observed result used to support verification or convergence.
- **Question:** an unresolved material uncertainty that may block a decision.
- **Clarification:** a recorded decision that resolves a question and identifies
  affected artifacts.
- **Implementation output:** source files produced from approved engineering
  context.

## Authority transition

The normal transition is:

```text
Draft → Proposal → Authoritative → Stale → Revalidated
```

The transition to Authoritative requires human approval. A content hash records
exactly what was approved.

## Stable identity

Requirements, acceptance criteria, tasks, questions, decisions, and findings
should retain stable identifiers when they are revised. This permits impact
analysis without relying on line numbers or document position.
