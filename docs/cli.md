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

## AI discovery

```powershell
thesys discovery propose
thesys discovery show
thesys question list
```

If the AI asks a blocking question:

```powershell
thesys question answer QST-001 "The platform must support ..."
thesys discovery propose
```

Only when the proposal is complete:

```powershell
thesys discovery accept
```

This creates the authoritative Intent and Engineering Context in one explicit human approval of the AI discovery proposal.

## Engineering stages

After Discovery, the standard v0.1.0 engineering sequence is:

```text
Context → Governance → Requirements → Clarification → Specification
→ Acceptance → Architecture → Quality → Security → Risk
→ Plan → Tasks → Implementation → Verification → Convergence → Release
→ Operation → Evolution → Retirement
```

For document stages, the normal proposal pattern is:

```powershell
thesys generate requirements
thesys proposal show requirements
thesys proposal accept requirements
```

The same `generate → proposal show → proposal accept` pattern applies to the
other document stages. If the AI raises blocking questions, answer them and
regenerate the proposal before approval. A question that is only a downstream
implementation, verification, release or operational condition does not by
itself block approval of the current baseline.

There is deliberately no general `stage approve` command. Approval without a current AI proposal is invalid by design.

### Engineering Units

Engineering Units are optional. A project can use the default unit directly;
when decomposition is useful, units can be created and related before or while
executing the lifecycle for their respective scopes. Unit-specific artifacts
are stored under the corresponding lifecycle stage and unit.

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
