---
thesys:
  schema: "4"
  methodology: "thesys-core"
  version: "0.1.0"
  language: "en-US"
lifecycle:
  stages:
    - id: intent
      name: Intent & Discovery
      artifact: engineering/intent/intent.md
      template: methodology/templates/intent.md
      approval: required
      depends_on: []
      action: discovery
      config:
        scope: project
    - id: context
      name: Engineering Context
      artifact: engineering/context/{unit}/context.md
      template: methodology/templates/context.md
      approval: required
      depends_on: [intent]
      action: document
      config:
        scope: unit
    - id: governance
      name: Governance & Constitution
      artifact: engineering/governance/governance.md
      template: methodology/templates/governance.md
      approval: required
      depends_on: [intent, context]
      action: document
      config:
        scope: project
    - id: requirements
      name: Requirements
      artifact: engineering/requirements/{unit}/requirements.md
      template: methodology/templates/requirements.md
      approval: required
      depends_on: [intent, context, governance]
      action: document
    - id: clarification
      name: Clarification
      artifact: engineering/clarification/{unit}/clarification.md
      template: methodology/templates/clarification.md
      approval: required
      depends_on: [requirements]
      action: document
    - id: specification
      name: Specification
      artifact: engineering/specification/{unit}/specification.md
      template: methodology/templates/specification.md
      approval: required
      depends_on: [requirements, clarification]
      action: document
    - id: acceptance
      name: Acceptance Criteria
      artifact: engineering/acceptance/{unit}/acceptance.md
      template: methodology/templates/acceptance.md
      approval: required
      depends_on: [requirements, specification]
      action: document
    - id: architecture
      name: Architecture & Design
      artifact: engineering/architecture/{unit}/architecture.md
      template: methodology/templates/architecture.md
      approval: required
      depends_on: [context, requirements, specification, acceptance]
      action: document
    - id: quality
      name: Quality Engineering
      artifact: engineering/quality/{unit}/quality.md
      template: methodology/templates/quality.md
      approval: required
      depends_on: [requirements, architecture]
      action: document
    - id: security
      name: Security Engineering
      artifact: engineering/security/{unit}/security.md
      template: methodology/templates/security.md
      approval: required
      depends_on: [context, requirements, architecture]
      action: document
    - id: risk
      name: Risk & Exception Analysis
      artifact: engineering/risk/{unit}/risk.md
      template: methodology/templates/risk.md
      approval: required
      depends_on: [requirements, architecture, quality, security]
      action: document
    - id: plan
      name: Implementation Plan
      artifact: engineering/plan/{unit}/plan.md
      template: methodology/templates/plan.md
      approval: required
      depends_on: [specification, architecture, quality, security, risk]
      action: document
    - id: tasks
      name: Tasks
      artifact: engineering/tasks/{unit}/tasks.md
      template: methodology/templates/tasks.md
      approval: required
      depends_on: [plan]
      action: document
    - id: implementation
      name: Implementation
      artifact: null
      template: methodology/templates/implementation.md
      approval: required
      depends_on: [requirements, specification, acceptance, architecture, quality, security, plan, tasks, risk]
      action: implementation
      config:
        scope: unit
    - id: verification
      name: Verification
      artifact: engineering/verification/{unit}/verification.md
      template: methodology/templates/verification.md
      approval: required
      depends_on: [implementation, requirements, acceptance, quality, security]
      action: verify
      config:
        command: "python -m pytest -q"
    - id: convergence
      name: Convergence
      artifact: engineering/convergence/{unit}/convergence.md
      template: methodology/templates/convergence.md
      approval: required
      depends_on: [intent, requirements, specification, architecture, risk, implementation, verification]
      action: document
    - id: release
      name: Release
      artifact: engineering/release/{unit}/release.md
      template: methodology/templates/release.md
      approval: required
      depends_on: [verification, convergence, risk]
      action: document
      config:
        delivery_milestone: true
    - id: operation
      name: Operation & Observability
      artifact: engineering/operations/{unit}/operations.md
      template: methodology/templates/operation.md
      approval: required
      depends_on: [release]
      action: document
    - id: evolution
      name: Evolution & Maintenance
      artifact: engineering/evolution/{unit}/evolution.md
      template: methodology/templates/evolution.md
      approval: required
      depends_on: [operation]
      action: document
    - id: retirement
      name: Retirement
      artifact: engineering/retirement/{unit}/retirement.md
      template: methodology/templates/retirement.md
      approval: required
      depends_on: [evolution]
      action: document
  rules:
    human_approval_required_before_progression: true
    proposals_are_non_authoritative: true
    human_may_only_approve_existing_ai_proposal: true
    changed_authoritative_artifact_invalidates_downstream: true
    unresolved_questions_block_affected_gate: true
    evidence_required_for_verification: true
    exceptions_require_explicit_risk_acceptance: true
    utf8: true
    blocking_markers: ["Status: Open", "BLOCKED", "TODO:DECISION"]
    implementation:
      output_root: "."
      allowed_roots: ["src", "app", "tests", "scripts", "migrations"]
      require_approved_context: true
      execute_generated_code: false
    verification:
      command: "python -m pytest -q"
---
