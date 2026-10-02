---
thesys:
  schema: "5"
  methodology: "thesys-core"
  version: "0.6.0"
  language: "en-US"
lifecycle:
  phases:
    - id: discovery-foundation
      name: Discovery & Foundation
      stages:
        - id: intent
          name: Intent & Discovery
          artifact: engineering/intent/intent.md
          template: methodology/templates/intent.md
          approval: required
          depends_on: []
          action: discovery
          config:
            artifact_prefix: INT
            scope: project
        - id: governance
          name: Governance & Constitution
          artifact: engineering/governance/governance.md
          template: methodology/templates/governance.md
          approval: required
          depends_on: [intent]
          action: document
          config:
            artifact_prefix: GOV
            scope: project
        - id: engineering-units
          name: Engineering Units
          artifact: engineering/units/engineering-units.md
          template: methodology/templates/engineering-units.md
          approval: required
          depends_on: [governance]
          action: units
          config:
            artifact_prefix: UNI
            scope: project

    - id: definition
      name: Definition
      stages:
        - id: context
          name: Engineering Context
          artifact: engineering/context/{unit}/context.md
          template: methodology/templates/context.md
          approval: required
          depends_on: [intent, governance, engineering-units]
          action: document
          config:
            artifact_prefix: CTX
            scope: unit
        - id: requirements
          name: Requirements
          artifact: engineering/requirements/{unit}/requirements.md
          template: methodology/templates/requirements.md
          approval: required
          depends_on: [intent, context, governance]
          action: document
          config:
            artifact_prefix: REQ
            scope: unit
        - id: clarification
          name: Clarification
          artifact: engineering/clarification/{unit}/clarification.md
          template: methodology/templates/clarification.md
          approval: required
          depends_on: [requirements]
          action: document
          config:
            artifact_prefix: CLR
            scope: unit
        - id: specification
          name: Specification
          artifact: engineering/specification/{unit}/specification.md
          template: methodology/templates/specification.md
          approval: required
          depends_on: [requirements, clarification]
          action: document
          config:
            artifact_prefix: SPE
            scope: unit
        - id: acceptance
          name: Acceptance Criteria
          artifact: engineering/acceptance/{unit}/acceptance.md
          template: methodology/templates/acceptance.md
          approval: required
          depends_on: [requirements, specification]
          action: document
          config:
            artifact_prefix: ACC
            scope: unit

    - id: design
      name: Design
      stages:
        - id: architecture
          name: Architecture & Design
          artifact: engineering/architecture/{unit}/architecture.md
          template: methodology/templates/architecture.md
          approval: required
          depends_on: [context, requirements, specification, acceptance]
          action: document
          config:
            artifact_prefix: ARC
            scope: unit
        - id: system-architecture
          name: System Architecture Integration
          artifact: engineering/architecture/system-architecture.md
          template: methodology/templates/system-architecture.md
          approval: required
          depends_on: [architecture]
          action: document
          config:
            artifact_prefix: ARC
            scope: project
            aggregate_units: true
            aggregate_relation: synthesizes

    - id: engineering-assurance
      name: Engineering Assurance
      stages:
        - id: quality
          name: Quality Engineering
          artifact: engineering/quality/{unit}/quality.md
          template: methodology/templates/quality.md
          approval: required
          depends_on: [requirements, architecture, system-architecture]
          action: document
          config:
            artifact_prefix: QRE
            scope: unit
        - id: security
          name: Security Engineering
          artifact: engineering/security/{unit}/security.md
          template: methodology/templates/security.md
          approval: required
          depends_on: [context, requirements, architecture, system-architecture]
          action: document
          config:
            artifact_prefix: SEC
            scope: unit
        - id: risk
          name: Risk & Exception Analysis
          artifact: engineering/risk/{unit}/risk.md
          template: methodology/templates/risk.md
          approval: required
          depends_on: [requirements, architecture, system-architecture, quality, security]
          action: document
          config:
            artifact_prefix: RSK
            scope: unit

    - id: delivery
      name: Delivery
      stages:
        - id: plan
          name: Implementation Plan
          artifact: engineering/plan/{unit}/plan.md
          template: methodology/templates/plan.md
          approval: required
          depends_on: [specification, architecture, system-architecture, quality, security, risk]
          action: document
          config:
            artifact_prefix: PLN
            scope: unit
        - id: tasks
          name: Tasks
          artifact: engineering/tasks/{unit}/tasks.md
          template: methodology/templates/tasks.md
          approval: required
          depends_on: [plan]
          action: document
          config:
            artifact_prefix: TSK
            scope: unit
        - id: implementation
          name: Implementation
          artifact: null
          template: methodology/templates/implementation.md
          approval: required
          depends_on: [requirements, specification, architecture, system-architecture, quality, security, plan, tasks, risk]
          action: implementation
          config:
            artifact_prefix: IMP
            scope: unit

    - id: verification
      name: Verification
      stages:
        - id: verification
          name: Verification
          artifact: engineering/verification/{unit}/verification.md
          template: methodology/templates/verification.md
          approval: required
          depends_on: [implementation, requirements, acceptance, quality, security]
          action: verify
          config:
            artifact_prefix: VER
            scope: unit
            command: "python -m pytest -q"
        - id: convergence
          name: Convergence
          artifact: engineering/convergence/{unit}/convergence.md
          template: methodology/templates/convergence.md
          approval: required
          depends_on: [intent, requirements, specification, architecture, system-architecture, risk, implementation, verification]
          action: document
          config:
            artifact_prefix: CON
            scope: unit

    - id: release-operation
      name: Release & Operation
      stages:
        - id: release
          name: Release
          artifact: engineering/release/{unit}/release.md
          template: methodology/templates/release.md
          approval: required
          depends_on: [verification, convergence, risk]
          action: document
          config:
            artifact_prefix: REL
            scope: unit
            delivery_milestone: true
        - id: operation
          name: Operation & Observability
          artifact: engineering/operations/{unit}/operations.md
          template: methodology/templates/operation.md
          approval: required
          depends_on: [release]
          action: document
          config:
            artifact_prefix: OPS
            scope: unit
        - id: evolution
          name: Evolution & Maintenance
          artifact: engineering/evolution/{unit}/evolution.md
          template: methodology/templates/evolution.md
          approval: required
          depends_on: [operation]
          action: document
          config:
            artifact_prefix: CHG
            scope: unit
        - id: retirement
          name: Retirement
          artifact: engineering/retirement/{unit}/retirement.md
          template: methodology/templates/retirement.md
          approval: required
          depends_on: [evolution]
          action: document
          config:
            artifact_prefix: RET
            scope: unit
  rules:
    human_approval_required_before_progression: true
    proposals_are_non_authoritative: true
    human_may_only_approve_existing_ai_proposal: true
    changed_authoritative_artifact_invalidates_downstream: true
    unresolved_questions_block_affected_gate: true
    question_blocking:
      model_decides: true
      blocking_definition: "The answer is necessary to approve or validly produce the current stage, or the decision cannot reasonably be deferred to a later stage."
      non_blocking_definition: "The information can legitimately be resolved later without invalidating the current stage."
      unresolved_blocking_questions_stop_progression: true
    evidence_required_for_verification: true
    exceptions_require_explicit_risk_acceptance: true
    engineering_units_are_a_first_class_lifecycle_stage: true
    engineering_units_control_complexity: true
    project_is_root_entity: true
    project_is_not_an_engineering_unit: true
    project_root_is_work_target_when_no_units_exist: true
    system_architecture_synthesizes_unit_architectures: true
    templates_define_artifact_structure: true
    agents_generate_section_content_only: true
    localization_is_structural_not_post_processed: true
    generated_code_is_never_executed_implicitly: true
    clarification_question_identity_is_runtime_owned: true
    clarification_question_ids_are_project_wide_and_canonical: true
    agents_must_not_assign_clarification_question_ids: true
    utf8: true
    blocking_markers: ["Status: Open", "BLOCKED", "TODO:DECISION"]
    implementation:
      output_root: "."
      allowed_roots: ["src", "app", "tests", "scripts", "migrations"]
      allowed_root_files: ["index.html", "README.md"]
      require_approved_context: true
      execute_generated_code: false
    verification:
      command: "python -m pytest -q"

---
