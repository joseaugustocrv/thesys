# Engineering Units

An engineering unit is the bounded object to which intent, requirements,
architecture, implementation and verification can be attached.

Units may be hierarchical: a system contains domains; domains contain
capabilities or modules; modules contain features, changes and defects. Each
unit may have dependencies and its own lifecycle state while remaining linked
to its parent context.

Supported unit types include system, domain, capability, epic, module, service,
feature, change, defect, migration, security remediation, architecture
initiative, technical debt and platform change.

Engineering Units are introduced through the **Engineering Units** lifecycle
stage. The stage produces the authoritative Engineering Unit Map (`UNI`) only
after human approval. Direct unit administration does not replace that gate.
