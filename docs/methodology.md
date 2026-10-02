# Thesys Methodology

Thesys is an executable software-engineering methodology for building software with human authority and AI execution working together.

## Core rule

The human owns intent, decisions, acceptance and risk. The AI analyzes, asks questions, proposes engineering artifacts and proposes implementation. A proposal is never authoritative until the human explicitly accepts that proposal.

The runtime enforces this rule rather than relying on team convention.

## End-to-end flow

The 0.5.0 delivery flow is:

```text
Human Intent Input
       ↓
AI Discovery
       ↓
Questions / Missing Information
       ↓
Human Answers
       ↓
AI Discovery Proposal
       ↓
Human Approval
       ↓
Authoritative Intent
       ↓
Governance
       ↓
Engineering Units (formal lifecycle stage)
       ↓
Requirements
       ↓
Clarification
       ↓
Specification
       ↓
Acceptance Criteria
       ↓
Architecture & Design
       ↓
Quality
       ↓
Security
       ↓
Risk & Exception Analysis
       ↓
Implementation Plan
       ↓
Tasks
       ↓
Implementation Proposal / Execution
       ↓
Verification
       ↓
Convergence
       ↓
Release
       ↓
Operation → Evolution → Retirement
```

For each document stage, the AI produces a non-authoritative proposal, questions are resolved as needed, and the responsible human explicitly accepts the proposal before it becomes authoritative. Implementation is controlled separately: the AI proposes changes and the runtime applies an accepted implementation proposal. Verification executes the configured verification command and records evidence.

Engineering Units control complexity through an explicit, approved lifecycle stage rather than representing arbitrary technical fragments. A small project uses the Project root as its single work target. When child Units exist, unit-scoped lifecycle work is performed independently for the relevant Units. After their local Architecture stages, the lifecycle returns to the project through System Architecture Integration, which synthesizes the approved Unit architectures into a system-level view without replacing them.

## Human responsibilities

The human:

- starts the work with the initial Intent;
- answers questions raised by the AI;
- reviews AI proposals and may accept them or add human guidance that causes the affected proposal and downstream work to be regenerated;
- makes business, architecture, risk and release decisions;
- accepts exceptions and residual risk;
- remains accountable for the resulting system.

The human does not have to manually author every engineering document.

## AI responsibilities

The AI:

- structures the initial Intent;
- identifies missing information and asks targeted questions;
- proposes Engineering Context;
- proposes requirements, specifications, architecture, quality and security artifacts;
- proposes implementation plans and code changes;
- analyzes verification evidence;
- identifies inconsistencies and convergence gaps;
- proposes changes when new information affects the engineering baseline.

AI output remains non-authoritative until explicitly accepted. Human guidance is also non-authoritative: it changes the inputs to proposal generation and propagates forward through the affected lifecycle scope.

## Lifecycle

The lifecycle is recursive and can be applied to a system, domain, module, service, capability, feature, defect, migration, security remediation, architectural initiative, technical debt item or other Engineering Unit.

The standard delivery path is:

`Intent → Governance → Engineering Units → Context → Requirements → Clarification → Specification → Acceptance → Unit Architecture → System Architecture Integration → Quality → Security → Risk → Plan → Tasks → Implementation → Verification → Convergence → Release`

After Release, the lifecycle continues through Operation, Evolution and Retirement.

Not every specialized workflow uses every stage in the same order. The methodology supports concurrent, iterative and recursive engineering rather than requiring one rigid waterfall sequence.
