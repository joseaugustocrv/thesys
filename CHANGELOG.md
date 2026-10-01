# Changelog

## 0.6.0 — Human guidance and propagated revalidation

- Added optional, durable Human Guidance as a first-class engineering input.
- Added CLI support for directives, review notes, references and UTF-8 text attachments.
- Guidance is included in proposal fingerprints and propagates forward through the affected lifecycle scope.
- Added automatic invalidation of non-authoritative proposals after guidance is added.
- Added revalidation/regeneration of approved downstream stages when guidance changes upstream context.
- Extended project documentation with Human Guidance history and lifecycle state indicators.
- Added status dots and explicit collapse affordances to lifecycle phase groups.
- Updated public documentation without exposing agent prompts, internal generation context or project-specific proposal data.

## 0.5.1 — Project as the lifecycle root

### Changed

- Made the Project entity the canonical root of the lifecycle and engineering hierarchy.
- Removed the synthetic `default` Engineering Unit from new projects.
- Project-scoped proposals, approvals and registry records now use the actual Project key.
- A project without Engineering Units uses the Project root as its single unit-scoped work target without materializing a fake Engineering Unit.
- Top-level Engineering Units now explicitly parent to the Project root.

### Fixed

- Updated lifecycle gates, dependency resolution, orchestration, implementation, documentation and CLI handling to use the same Project-root model.
- Added conservative migration of 0.5.0 `default` root state into the Project-root model.
- Preserved compatibility with legacy Engineering Unit proposals that used `default`/`project` as the root parent token.

### Validation

- Full automated test suite: 77 tests passed.

## 0.5.0 — hierarchical lifecycle and structured orchestration

### Added

- Introduced hierarchical lifecycle phases with stages as the only workflow gates.
- Promoted Engineering Units to a first-class, human-approved lifecycle stage.
- Added the authoritative Engineering Unit Map artifact and canonical lifecycle proposal storage.
- Added presentation-safe generated documentation that exposes lifecycle progress without project artifact content.

### Changed

- Reworked orchestration to follow the methodology dependency graph without hidden Engineering Unit transitions or phase-level approval semantics.
- Extended the methodology contract with explicit phase metadata, stage scope, action and dependencies.
- Kept project/unit as the only lifecycle scopes; project-level aggregation remains an explicit stage capability.
- Strengthened agent lifecycle context with phase and stage information while keeping prompts methodology-owned and provider adapters generic.
- Improved generated HTML navigation to reflect the same runtime lifecycle status used by the CLI.

### Fixed

- Fixed lifecycle documentation status projection so an approved stage cannot appear as partially approved because the HTML inferred a different Unit set.
- Fixed clarification-history projection so durable answered decisions remain attached to authoritative artifacts after regeneration and acceptance.
- Preserved compatibility with accepted 0.4.0 Engineering Unit proposals during migration.

### Validation

- Full automated test suite and deterministic end-to-end lifecycle verification must pass before the 0.5.0 tag is created.

## Unreleased

### Changed

- Removed lifecycle metadata (status, proposal authority and artifact placeholder version/owner fields) from generated artifact prose. Lifecycle state remains represented by Thesys runtime metadata and the registry.
- Centralized agent policy and stage-specific generation guidance in the methodology-owned `methodology/agents/prompts.json` contract.
- Strengthened document-generation guidance so proposals are implementation-enabling, distinguish known facts from proposed decisions, and ask blocking questions when a current-stage decision is genuinely unresolved.
- Fixed documentation navigation for lifecycle stages that share an artifact prefix, notably Architecture and System Architecture.
- Added localized documentation-shell labels and explicit lifecycle stage metadata to the documentation manifest.
- Approval now materializes the approved proposal content without rewriting its document body.


## 0.4.0 — clarification and documentation convergence

- Clarification-question identity is now assigned by the runtime using project-wide canonical `QST-NNN` identifiers; AI schemas no longer accept model-assigned IDs.
- Preserved question identity and clarification history across regeneration while preventing answered decisions from being reintroduced.
- Structured generation contracts now keep document structure, localization and generated content as separate responsibilities.
- Installed wheels resolve bundled methodology resources correctly without relying on the source repository layout.

- Preserve answered clarification history across AI proposal regeneration.
- Prevent answered questions from returning under different wording or identifiers.
- Generate unit-scoped lifecycle proposals as a phase batch while retaining independent proposal state per Unit.
- Expose current non-authoritative proposals and clarification history in generated HTML documentation.
- Improve pt-BR generation by localizing human-readable headings and normative language.
- Write generated JSON as UTF-8 without a BOM, with explicit UTF-8 decoding for Windows compatibility.



## 0.4.0 - 2026-09-28

### Added
- Enforced the `Thesys Projects` workspace boundary for project initialization and creation.
- Added project-level System Architecture Integration that synthesizes approved Engineering Unit architectures.
- Added aggregate lifecycle dependency handling and cross-Unit architecture traceability.

### Changed
- Engineering Units now explicitly control complexity for larger systems; the default system unit becomes a container when child Units exist.
- Unit-scoped lifecycle stages remain independent, while System Architecture provides an integrated project-level view before Quality, Security and Risk.
- Registry artifact identifiers now consistently use methodology-defined prefixes for every lifecycle stage.
- Updated methodology, templates, CLI documentation, bundled methodology and tests to reflect the revised model.
- `thesys next` now orchestrates the lifecycle by automatically proposing the next ready AI activity without bypassing human approval.
- Engineering Unit decomposition can explicitly decline to split a small project, preserving the default system unit.
- Project documentation is refreshed automatically after meaningful lifecycle mutations.

### Validation
- Full automated test suite: 31 passed.
- End-to-end lifecycle validation completed with the deterministic provider through Retirement.
- Multi-Unit validation completed through System Architecture Integration.
- Wheel build and isolated installation validation completed.

## 0.3.0 - 2026-09-28

### Added

- Added project language configuration for generated engineering content.
- Added language-aware AI generation while preserving canonical methodology structure.
- Added automated coverage for project language behavior and language fallback.
- Added consolidated HTML documentation with embedded Thesys branding/logo.
- Added HTML documentation coverage for embedded logo rendering.

### Changed

- Generated engineering content now follows the configured project language.
- Methodology structure and canonical artifact identifiers remain language-independent.
- Improved documentation generation and HTML presentation.

### Validation

- Validated AI-assisted project generation using OpenAI with `pt-BR`.
- Validated AI-assisted project generation using OpenAI with `en-US`.
- Validated generated HTML documentation in both language configurations.
- Validated embedded Thesys logo rendering in generated HTML.

## 0.2.1 - 2026-09-28

### Fixed

- Fixed authoritative artifact status materialization after human approval.
- Approved artifacts now reflect `Authoritative` status in their own Markdown content.
- Preserved proposal technical content while normalizing explicit status metadata at the human-approval boundary.
- Added regression coverage for authoritative artifact materialization.
- Added validation that the materialized artifact remains consistent with the registry and approval hash.

### Validation

- 16 automated tests passing, including the complete lifecycle and authoritative artifact regression coverage.
- Python compilation checks passing.
- Project initialization and validation smoke-tested.

## 0.2.0 - 2026-09-28

### Added

- Added first-class project identity and methodology-defined project templates.
- Added project creation, listing, inspection, active-project selection and template discovery commands.
- Separated reviewable engineering artifacts from public `docs/` documentation.
- Added conservative migration of registered legacy `docs/` artifacts into `engineering/`.
- Required a current human-approved Intent before engineering-unit proposals can be generated.
- Added proposal input fingerprints to prevent acceptance of stale downstream proposals.
- Added engineering-unit hierarchy and dependency cycle validation.
- Added project structure, active-project resolution and lifecycle end-to-end coverage.
- Added consolidated HTML documentation with lifecycle navigation and traceability of related artifacts.
- Added static documentation generation through the `docs build` command.

### Changed

- Project-scoped commands can resolve the active project from a workspace, while explicit `--path` project paths remain supported.
- Project keys are validated before filesystem operations.
- The default project template is now defined by the methodology template catalog rather than hard-coded in the CLI.
- Lifecycle artifacts are stored under the project `engineering/` root.
- Existing `thesys init --path .` remains supported for initializing an existing repository.
- Documentation generation follows the lifecycle order defined by the methodology.

## 0.1.0 - 2026-09-26

### Added

- Introduced Thesys as an independent, methodology-driven software engineering runtime.
- Defined an executable software engineering lifecycle from governance and intent through requirements, specification, architecture, planning, implementation, verification, convergence, release, operation, evolution and retirement.
- Added governance and engineering context as first-class lifecycle concerns.
- Added explicit acceptance, quality, security and risk controls.
- Added a capability catalog for artifact types, relations, engineering-unit types, specialized workflows and gate families.
- Added recursive engineering-unit hierarchy to support large systems and modular development.
- Added structural artifact registry and traceability graph support.
- Added evidence records and relationships to engineering artifacts.
- Added change registration and impact inspection capabilities.
- Added specialized workflows for features, defects, changes, security, migration, architecture and technical debt.
- Added expanded methodology templates covering governance, context, requirements, acceptance, quality, security, risk, operation, evolution and retirement.
- Added human approval gates and authoritative artifact hashing.
- Added downstream invalidation after changes to authoritative artifacts.
- Added proposal storage and acceptance flow.
- Added explicit human Intent input; project initialization no longer fabricates an Intent.
- Added AI-assisted Engineering Unit decomposition with non-authoritative proposals, review, acceptance, hierarchy and Intent lineage.
- Added proposal staleness protection when the authoritative Intent changes.
- Added dependency fingerprints so downstream approvals and executable stages become stale when upstream authority changes.
- Added deterministic end-to-end lifecycle coverage through implementation, verification, release and retirement, including backward revalidation.
- Added mock and OpenAI structured-output agent support.
- Added implementation file generation through methodology-defined actions.
- Added public methodology documentation and a centralized, versioned agent prompt contract.
- Added deterministic CLI and validation paths for project initialization, human Intent, Engineering Units, evidence, changes and repository validation.

### Changed

- OpenAI is now the default AI provider for methodology project templates.
- The OpenAI SDK is a runtime dependency rather than an optional extra.
- Project-scoped AI commands resolve the configured provider automatically.
- Explicit `--agent mock` remains available for deterministic testing and local development.
- Added clear CLI errors for missing OpenAI configuration or SDK installation.
- Refined the documentation site branding with the standalone Thesys mark, a neutral engineering palette and a more focused landing page.

### Validation

- 15 automated tests passing, including a realistic Intent-to-retirement lifecycle and upstream-change backtracking scenario.
- Python compilation checks passing.
- Project initialization and validation smoke-tested.
- No legacy methodology-name references remain in the repository.