# Engineering model

Thesys treats engineering information as a connected model rather than a collection of unrelated documents.

## Engineering units

A system can be decomposed into connected engineering scopes:

```text
System
├── Domain
│   ├── Module
│   ├── Service
│   └── Capability
├── Platform
└── Infrastructure
```

The same model can be applied recursively. A large system can therefore be managed as many connected units without forcing every decision into one enormous document.

## Artifacts

Artifacts represent important engineering knowledge. Depending on context, they may describe intent, requirements, specifications, decisions, risks, security concerns, plans, tasks, verification, changes, releases or operational findings.

An artifact has meaning beyond its text. Its lifecycle includes identity, state, authority, ownership and relationships to other engineering information.

## Relationships

The important question is not only "what does this artifact say?" but also "what does this decision affect?"

A typical relationship chain is:

```text
Requirement
   ↓
Acceptance criterion
   ↓
Architecture decision
   ↓
Task
   ↓
Test
   ↓
Verification evidence
```

Traceability is intentionally selective. It focuses on significant behavior, decisions, risks and evidence instead of requiring meaningless mappings for every line of code.

## Authority and proposals

Thesys distinguishes candidate material from authoritative engineering decisions. This is particularly important when AI participates in drafting or analysis. A useful proposal can accelerate work without becoming a decision merely because it was generated.

## Evidence

Evidence records what was observed, when it was observed, how it was produced and what engineering subject it supports. Evidence can therefore remain useful after the original activity has finished.

## Large-system value

The model supports both local and system-level reasoning. A module can maintain detailed engineering knowledge while remaining related to domain-level and system-level decisions. This allows large systems to evolve without losing their higher-level context.
