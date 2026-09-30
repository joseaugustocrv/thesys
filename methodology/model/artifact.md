# Artifact Model

Every authoritative engineering artifact has machine-addressable metadata such
as identity, type, version, lifecycle status, authority, ownership, source,
relationships, dependencies, approvals, risks and change history. Content is
the engineering knowledge itself; lifecycle metadata must not be duplicated
as prose inside the artifact.

## States

`draft → proposed → authoritative → stale → superseded`

A proposal never becomes authoritative merely because it was generated. An
approval is bound to the exact content version it approved.
