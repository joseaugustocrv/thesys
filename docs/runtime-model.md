# Runtime Model

## Authority boundary

Thesys separates three kinds of state:

1. **Human input** — the initial Intent and answers to AI questions.
2. **AI proposals** — derived engineering content that is explicitly non-authoritative.
3. **Authoritative artifacts and evidence** — content accepted by a human or produced by the runtime as execution evidence.

The runtime prevents a proposal from becoming authoritative merely because it exists.

## Proposal contract

Every AI proposal carries:

- proposal identity;
- lifecycle stage and Engineering Unit;
- provider;
- input fingerprint;
- creation timestamp;
- proposed content;
- questions and blocking state;
- durable clarification history, including answered question, human answer and proposal context;
- acceptance state.

Changing an answer or an upstream authoritative artifact invalidates the proposal and forces regeneration. Regeneration carries the clarification history forward and must not recreate an answered clarification under different wording. A human declaration that information is not yet known remains explicit uncertainty; it is not converted into a new blocking question for the same information category.

## Execution contract

Implementation is also a proposal. The runtime validates every generated path against methodology-defined allowed roots and applies the proposal only after human acceptance. Generated code is not executed implicitly.

Verification is different: the runtime executes the configured verification command, records the result as evidence, and asks the AI to interpret that evidence. A failed verification creates a blocking condition.

## Scope model

Project-scoped artifacts include Intent, Governance, Engineering Units and System Architecture. Engineering Context and downstream delivery/verification artifacts may be unit-scoped. A project can therefore contain a hierarchy such as:

```text
System
├── Domain
│   ├── Module
│   │   ├── Feature
│   │   └── Defect
│   └── Service
└── Platform
    ├── Identity
    └── Observability
```

Project-level stages provide project-wide constraints and integration points; unit-scoped stages remain independently controlled for each applicable Engineering Unit. When no Engineering Units exist, the Project root itself is the single work target for unit-scoped lifecycle stages. Once child Units exist, only those Units receive unit-scoped lifecycle artifacts; the Project remains the root entity and receives project-scoped stages.

## Change propagation

Authoritative content is fingerprinted at approval. If it changes, its stage becomes `needs_revalidation`, dependent stages become stale or blocked, and the next proposal must be generated from the new source of truth.

## Delivery boundary

Release is the delivery milestone. Operation, Evolution and Retirement remain part of the full lifecycle and can continue after delivery.
