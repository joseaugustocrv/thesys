# Artifact Model

Every authoritative engineering artifact has an identity, type, version,
status, authority, owner, source, parent/child relationships, dependencies,
traceability relations, decisions, evidence, approvals, risks and change
history. Content is one part of the artifact; metadata makes its engineering
meaning machine-addressable.

## States

`draft → proposed → authoritative → stale → superseded`

A proposal never becomes authoritative merely because it was generated. An
approval is bound to the exact content version it approved.
