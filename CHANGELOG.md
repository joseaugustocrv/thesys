# Changelog

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
- Added public methodology documentation while keeping proprietary prompt and orchestration material outside the distributable methodology surface.
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