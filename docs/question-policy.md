# Clarification-question policy


## Decision

The LLM owns the semantic decision of whether a generated question is blocking.
The runtime does not classify question meaning using keywords, topic lists, or
stage-specific regular expressions.

The methodology is authoritative. `methodology/definition/lifecycle.md` defines
the blocking policy. The agent receives the complete lifecycle graph, the current
stage, upstream artifacts, and the policy when generating questions.

The runtime remains responsible for structural guarantees:
- question IDs are allocated by the runtime;
- `blocking` must be a boolean;
- unanswered blocking questions prevent progression;
- proposal approval still requires human approval;
- question history and regeneration remain runtime-owned.

Executable stages are also handled by their dedicated execution paths:
Implementation uses `implementation propose/accept`; Verification runs the
configured verification command before generating its proposal.

## Validation

- `python -m pytest -q` → 74 passed
- `python -m compileall -q engine/thesys_engine` → passed
- Full mock-agent E2E → 45 transitions from Intent through Retirement
- E2E covered Context, Requirements, Clarification, Specification, Acceptance,
  Architecture, System Architecture, Quality, Security, Risk, Plan, Tasks,
  Implementation, Verification, Convergence, Release, Operation, Evolution and
  Retirement.

No generated-project compatibility behavior is preserved by this refactor;
projects will be recreated from the new methodology/runtime baseline.
