# Structural Traceability

Traceability follows meaningful engineering intent through its derived forms:

`INT → CTX → REQ → CLR → SPE → ACC → ARC(Unit) → ARC(System) → PLN → TSK → CODE → TST → EVD → VER → CON → REL`

Not every code line needs a requirement identifier. Significant behavior,
decisions, risks, controls and verification claims must remain followable.

## Architecture synthesis

Unit architecture artifacts remain authoritative within their Unit boundaries. `ARC(System)` is a project-level integration view that synthesizes approved Unit architectures, their dependencies, boundaries and cross-Unit interfaces. It does not replace the Unit architecture artifacts.
