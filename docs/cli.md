# CLI Workflow

The CLI exposes the methodology without requiring the user to select an AI agent at every command. The configured project provider is used by default. `--agent mock` is an explicit test override; production projects default to OpenAI.

## Start a project

```powershell
thesys project create finance-platform
```

Then provide the human Intent:

```powershell
thesys intent create "Create a personal finance platform for managing income, expenses, budgets, financial indicators, bank transaction imports, alerts, notifications, and secure authentication."
```

## AI-driven progression

The normal workflow is state-driven. After the human Intent is created, `thesys next` identifies the first action whose dependencies are satisfied and, when that action is an AI proposal, generates it automatically using the configured provider.

```powershell
thesys next
```

The command never silently approves an artifact. It can:

- generate the next AI proposal when all declared dependencies are current;
- stop for human review when a current proposal is waiting for approval;
- stop for blocking questions or stale proposals;
- execute the configured Verification action when its dependencies are current;
- report completion when the selected lifecycle scope is fully current.

The explicit lower-level commands remain available for advanced workflows, automation, troubleshooting and provider overrides.

### Discovery

Provide the human Intent first:

```powershell
thesys intent create "Create a personal finance platform..."
thesys next
```

`next` generates the discovery proposal. If the AI raises a blocking question, answer it and run `thesys next` again; the proposal is regenerated only after the human answer changes its inputs. Discovery acceptance remains explicit:

```powershell
thesys discovery accept
```

Discovery approval establishes the authoritative Intent and the initial Engineering Context together.

### Engineering Units

Engineering Units are a first-class lifecycle stage under **Discovery & Foundation**. After Governance is approved, `thesys next` proposes the Unit structure using the configured AI provider. The proposal is non-authoritative and must be explicitly accepted:

```powershell
thesys next
thesys proposal show engineering-units
thesys proposal accept engineering-units
```

`thesys unit propose` and `thesys unit proposal accept` remain compatibility-oriented convenience commands over the same lifecycle stage. They do not create a second workflow.

Engineering Units control complexity. A small project uses the Project root as its single work target; when child Units are introduced, unit-scoped lifecycle work moves to those Units while the Project remains the root entity.

### Engineering stages

After Engineering Units is approved, the methodology's dependency graph drives
progression. Unit-scoped stages are planned as a batch, but each Unit retains
its own proposal, questions, approval and traceability. The stage itself remains
the gate; a phase is only a grouping/navigation concept.

```text
Discovery & Foundation
  Intent → Governance → Engineering Units
Definition
  Context → Requirements → Clarification → Specification → Acceptance
Design
  Architecture → System Architecture
Engineering Assurance
  Quality → Security → Risk
Delivery
  Plan → Tasks → Implementation
Verification
  Verification → Convergence
Release & Operation
  Release → Operation → Evolution → Retirement
```

### Continuous documentation

The project documentation is a generated projection of the current Thesys state. Meaningful lifecycle mutations refresh `.thesys/docs/index.html` automatically. It can also be rebuilt explicitly:

```powershell
thesys docs build
```

The HTML documentation includes lifecycle progress, authoritative artifacts, current non-authoritative proposals, proposal questions, approval state, clarification history, evidence and traceability context where available. Proposals are explicitly distinguished from authoritative artifacts and are never treated as approved merely because they appear in the site.

## Implementation

```powershell
thesys implementation propose
thesys implementation show
thesys implementation accept
```

The last command applies the already reviewed AI code proposal. It does not execute the generated code.

## Verification

```powershell
thesys verify
thesys proposal show verification
thesys proposal accept verification
```

The runtime executes the configured verification command and records evidence. A failed verification creates a blocking condition instead of being silently accepted.

## Traceability and change

```powershell
thesys trace REQ-001
thesys change create accounts "Import support" "Add bank transaction import capability."
thesys change impact CHG-001
```

Changing an authoritative artifact invalidates dependent artifacts. They must be re-proposed from the new source of truth.

### Presentation-safe documentation

For an investor, executive or other external audience, Thesys can generate a
business-safe lifecycle overview that contains methodology state and stage
progress but omits project artifact content, questions, identifiers, paths and
other technical/project data:

```powershell
thesys docs build --presentation
```

The normal `thesys docs build` remains the detailed engineering projection for
internal use.

## Human guidance

When a proposal needs a different direction, the human can add optional guidance instead of relying on an implicit rejection. Guidance is durable, non-authoritative and becomes part of proposal generation inputs. Adding guidance to a stage invalidates the affected proposal and propagates revalidation to downstream stages.

```powershell
thesys guidance add requirements directive "Use only BRL in the MVP." --unit financial-records
thesys guidance add requirements review-note "Do not introduce audit history in the MVP." --unit financial-records
thesys guidance add requirements reference "Use this reference." --file .\reference.md --unit financial-records
thesys guidance list
```

The project documentation shows applicable guidance in the same right-hand engineering history area as questions and clarification history. Public/presentation documentation does not expose project-specific guidance or internal AI generation context.
