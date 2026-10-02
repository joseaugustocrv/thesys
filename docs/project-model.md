# Project model

A Thesys project is the concrete engineering workspace in which the
methodology is executed. The methodology is shared and authoritative; each
project is an instance with its own identity, Intent, engineering units,
artifacts, evidence and lifecycle state.

## Project creation

A project can be created from a methodology-defined project template:

```text
thesys project create finance-platform \
  --name "Personal Finance Platform" \
  --template software-system
```

Templates define a starting project profile such as the project kind, root
engineering-unit type, initial workspace directories and default AI provider
provider. A template does not replace the methodology and does not prevent a
project from evolving into a more complex structure.

Available templates are discoverable from the CLI:

```text
thesys project templates
```

## Project workspace

A project separates Thesys runtime state from human-reviewable engineering
artifacts and from the software being built:

```text
project/
├── .thesys/
│   ├── project.yaml
│   ├── config.yaml
│   ├── units/
│   ├── proposals/
│   ├── evidence/
│   ├── changes/
│   ├── executions/
│   ├── registry.json
│   └── approvals.json
│
├── engineering/
│   ├── governance/
│   ├── context/
│   ├── intent/
│   ├── requirements/
│   ├── clarification/
│   ├── specification/
│   ├── acceptance/
│   ├── architecture/
│   ├── quality/
│   ├── security/
│   ├── risk/
│   ├── plan/
│   ├── tasks/
│   ├── verification/
│   ├── convergence/
│   ├── release/
│   ├── operations/
│   ├── evolution/
│   └── retirement/
│
├── src/
└── tests/
```

`engineering/` contains reviewable engineering artifacts. `.thesys/`
contains runtime metadata and execution state. Ordinary project documentation
can remain in `docs/` without being confused with Thesys lifecycle artifacts.

## Project → Intent → Lifecycle / Engineering Units

The minimum project path is:

```text
Project
  ↓
Intent & Discovery
  ↓
Governance
  ↓
Engineering Units (approved stage)
  ↓
Lifecycle execution
```

Engineering Units are the mechanism for controlling complexity in larger scopes. A small project uses the Project root as its single work target. When a project benefits from separate Engineering Units, the human can introduce them from the authoritative Intent:

```text
Authoritative Intent
  ↓
Engineering Unit Proposal
  ↓
Human review and acceptance
  ↓
Authoritative Engineering Unit Map
  ↓
Lifecycle execution per relevant Unit
```

A simple project may continue with the Project root as its only work target without an explicit
decomposition step. Larger systems can use multiple units and preserve parent,
dependency and traceability relationships between them.

The human owns the source Intent input. The configured AI provider may refine
that input into a non-authoritative Intent proposal. The responsible human
accepts the proposal to make the Intent authoritative. Engineering Unit
proposals are likewise non-authoritative until explicitly accepted.

## Recursive project structure

Large systems can be decomposed recursively:

```text
System
├── Domain
│   ├── Capability
│   └── Module
├── Platform
│   ├── Identity
│   └── Observability
└── Infrastructure
```

Each unit can carry its own context, requirements, specification, acceptance, local architecture, plan, implementation and verification while retaining parent, dependency and traceability relationships. When multiple Units exist, the Project remains the root entity and unit-scoped work is performed by those Units. The lifecycle then returns to a project-level System Architecture Integration stage that synthesizes the approved Unit architectures into a system view without replacing them.

## Changing an Intent

The Intent is a source artifact, not a one-time prompt. When its authoritative
content changes, the approval fingerprint changes and dependent engineering
work becomes subject to revalidation. The project can therefore move backward
in the lifecycle without losing its existing history.
