# Agent prompts and adapter contract

The file `prompts.json` is the canonical methodology-owned prompt contract for AI agents. Provider adapters must load these instructions and combine them with the structured-output schema supplied by the runtime.

## Separation of responsibilities

- `methodology/agents/prompts.json`: engineering policy, stage-specific depth, question policy and output discipline.
- `engine/thesys_engine/agents.py`: provider adapter, structured-output schema and runtime context assembly.
- `methodology/templates/`: artifact structure and section hierarchy.
- `methodology/localization/`: human-facing structural labels.

A new agent provider should therefore implement only the provider-specific call/response adapter. It must not copy lifecycle rules into a second prompt implementation.

## Required provider contract

1. Load the prompt catalog.
2. Compose the common policy and the current stage policy.
3. Supply authoritative artifact content and the runtime artifact index.
4. Supply the complete lifecycle contract for question classification.
5. Enforce the JSON schema returned by the runtime.
6. Never assign clarification-question IDs.
7. Preserve the distinction between known facts, approved decisions and new proposals.

Provider-specific instructions may constrain output further, but must not weaken the methodology contract.
