# Workflows

Thesys uses a common control model with specialized workflows.

## Feature / capability

For a feature or capability within the standard project lifecycle, the flow is:

`Intent → Context → Governance → Requirements → Clarification → Specification → Acceptance → Architecture → Quality → Security → Risk → Plan → Tasks → Implementation → Verification → Convergence → Release`

Project-level Context and Governance may already be established and inherited
by the affected unit. Specialized work does not require duplicating those
artifacts when they are already authoritative for the project.

## Defect

`Observation → Diagnosis → Root/Contributing Cause → Correction → Symptom Verification → Regression Verification → Convergence`

## Change

`Change Request → Impact Analysis → Affected Artifacts → Decision → Revalidation → Implementation → Verification → Convergence`

## Security

`Security Need → Threat/Risk Analysis → Security Requirements → Architecture Controls → Implementation Controls → Security Verification → Evidence`

## Migration

`Current State → Target State → Compatibility → Migration Plan → Migration → Validation → Rollback/Recovery → Convergence`

Every workflow retains explicit authority, questions, traceability, evidence and human approval where the selected controls require it.
