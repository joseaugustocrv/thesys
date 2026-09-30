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

Once the project-level discovery/governance baseline is current, `thesys next` automatically asks the configured AI provider to propose Engineering Units. The proposal is non-authoritative and must be explicitly accepted:

```powershell
thesys next
thesys unit proposal accept
```

The normal workflow therefore does not require the user to remember `unit propose`. The explicit `unit propose` command remains available for advanced/manual workflows.

Engineering Units control complexity. A small project may remain on the default system unit; when child Units are introduced, unit-scoped lifecycle work moves to those Units and the default becomes the project/system container.

### Engineering stages

After the structural setup, the methodology's dependency graph drives progression automatically. For unit-scoped phases, `next` plans the phase as a batch: it generates proposals for all applicable Engineering Units, keeps each proposal independently persisted, and blocks phase approval until all blocking clarifications are resolved:

```text
Context → Governance → Engineering Units → Requirements → Clarification → Specification
→ Acceptance → Unit Architecture → System Architecture Integration
→ Quality → Security → Risk → Plan → Tasks → Implementation → Verification → Convergence → Release
→ Operation → Evolution → Retirement
```

For ordinary document stages, the equivalent explicit commands remain:

```powershell
thesys generate requirements
thesys proposal show requirements
thesys proposal accept requirements
```

`thesys next` is the recommended path; the explicit commands are retained as lower-level controls. Human approval remains required before progression, and an authoritative upstream change invalidates dependent artifacts.

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
