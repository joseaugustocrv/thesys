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

## Project → Intent → Engineering Units

The normal entry path is:

```text
Project
  ↓
Intent
  ↓
Engineering Unit Proposal
  ↓
Human review and acceptance
  ↓
Engineering Units
  ↓
Lifecycle execution
```

The human owns the source Intent input. The configured AI provider may refine
that input into a non-authoritative Intent proposal. The responsible human
accepts the proposal to make the Intent authoritative. AI or deterministic
providers may then propose Engineering Units from that authoritative Intent,
but those proposals remain non-authoritative until accepted by the responsible
human.

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

Each unit can carry its own context, requirements, architecture, plan,
implementation and verification while retaining parent, dependency and
traceability relationships.

## Changing an Intent

The Intent is a source artifact, not a one-time prompt. When its authoritative
content changes, the approval fingerprint changes and dependent engineering
work becomes subject to revalidation. The project can therefore move backward
in the lifecycle without losing its existing history.
