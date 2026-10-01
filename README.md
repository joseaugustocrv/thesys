# Thesys

> **Methodology becomes executable.**

Thesys is a software engineering methodology and runtime for turning human
intent into controlled, traceable and verifiable software with AI assistance.

The methodology covers the full engineering lifecycle and is designed to scale
from a small feature to systems composed of many domains, modules and services.
It can operate inside Agile, Scrum, Kanban, DevOps or other delivery models.

## Engineering lifecycle

Thesys separates **lifecycle phases** from **lifecycle stages**. Phases organize
the journey; every stage is an executable gate with its own dependencies,
scope, proposal and human approval.

```text
DISCOVERY & FOUNDATION
  Intent → Governance → Engineering Units

DEFINITION
  Context → Requirements → Clarification → Specification → Acceptance

DESIGN
  Architecture → System Architecture

ENGINEERING ASSURANCE
  Quality → Security → Risk

DELIVERY
  Plan → Tasks → Implementation

VERIFICATION
  Verification → Convergence

RELEASE & OPERATION
  Release → Operation → Evolution → Retirement
```

The lifecycle is recursive rather than strictly linear. Specialized workflows
exist for features, defects, changes, migrations, security work, architecture
initiatives and technical debt.

## Core principles

- Intent is explicit before implementation.
- Authority is explicit and human decisions remain attributable.
- AI output is proposal material until accepted.
- Traceability follows significant engineering intent and decisions.
- Changes propagate from their authoritative source to derived artifacts.
- Verification produces evidence rather than unsupported assertions.
- Security, quality, operability and maintainability are integrated into
  engineering.
- Rigor is proportional to risk and system impact.
- Large systems are decomposed into recursively manageable engineering units.
- Exceptions require explicit risk acceptance.

## Product architecture

```text
Methodology definition
        ↓
Generic runtime
        ↓
CLI / project execution
```

The methodology defines the engineering model. The runtime executes that model
without embedding a project-specific lifecycle sequence in the CLI.

## Repository structure

```text
methodology/     Executable methodology, models, workflows, policies, prompts and templates
docs/            Public methodology and product documentation
engine/          Generic runtime and CLI implementation
tests/           Automated verification
scripts/         Repository quality checks
assets/          Thesys visual identity
.github/         CI and documentation workflows
```

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
thesys --version
```

AI-assisted commands use OpenAI by default. Configure the API key in the
environment or in a local `.env` file (never commit it):

```text
OPENAI_API_KEY=...
THESYS_OPENAI_MODEL=gpt-5.6-luna
```

A project can explicitly select `mock` for deterministic testing, but `mock`
is never the default: `thesys config set agent_provider mock`.

Start with the human Intent. Thesys then drives an AI discovery loop; it does not ask the human to manually construct the Engineering Context first:

```powershell
thesys intent create "Create a personal finance platform for managing income, expenses, budgets, alerts and secure authentication."
thesys discovery propose
thesys discovery show
thesys question list
# answer any blocking questions
thesys question answer QST-001 "..."
thesys discovery propose
thesys discovery accept
```

After discovery is accepted, each engineering stage follows the same controlled pattern: AI proposes, the human answers blocking questions, and the human accepts the resulting proposal. There is intentionally no generic `stage approve` shortcut.

Create a project from a methodology template:

```powershell
thesys project templates
thesys project create finance-platform --name "Personal Finance Platform" --template software-system
thesys project info finance-platform
thesys status
```

The project created by `project create` becomes the active project for the
workspace. With multiple projects, select one explicitly with
`thesys project use <key>`. For an existing repository,
`thesys init --path .` remains available.

Engineering Units are introduced through the lifecycle rather than by a hidden or separate decomposition workflow:

```powershell
thesys next
thesys proposal show engineering-units
thesys proposal accept engineering-units
```

The low-level `thesys unit create` command remains available for controlled maintenance and migration scenarios; it does not bypass the Engineering Units lifecycle gate.

Inspect traceability or record evidence:

```powershell
thesys trace REQ-001 --path .
thesys evidence record verification:billing PASS --related REQ-001 --path .
```

The authoritative lifecycle is defined in
`methodology/definition/lifecycle.md`, with the capability catalog in
`methodology/definition/catalog.json`. Agent policy is centralized in
`methodology/agents/prompts.json` so new provider adapters do not duplicate
lifecycle rules.
