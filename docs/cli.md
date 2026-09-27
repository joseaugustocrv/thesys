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

For each stage the normal pattern is:

```powershell
thesys generate requirements
thesys proposal show requirements
thesys proposal accept requirements
```

If the AI raises questions, answer them and regenerate the proposal before approval.

There is deliberately no general `stage approve` command. Approval without a current AI proposal is invalid by design.

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
