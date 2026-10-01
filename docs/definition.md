# Methodology definition

Thesys maintains an executable representation of its engineering model so that tooling can interpret lifecycle behavior consistently.

## What a methodology can define

An executable methodology may describe:

- lifecycle activities;
- engineering relationships;
- artifact expectations;
- dependencies;
- approval requirements;
- validation rules;
- generic action types;
- applicable templates.

The important architectural principle is that the runtime interprets these definitions rather than embedding a project-specific lifecycle sequence in its implementation. The definition is hierarchical: phases organize stages, while stages remain the only workflow gates.

## Public methodology versus internal implementation

The public documentation explains engineering principles, responsibilities and expected outcomes. It does not need to expose proprietary prompts, internal orchestration, private heuristics or implementation details that are not necessary to understand the methodology.

## Methodology evolution

A methodology is itself versioned engineering knowledge. Changes should be reviewed for internal consistency, validated and released deliberately.

A change to an executable definition can affect project behavior. A change to public documentation changes how the methodology is explained. Those concerns are related but distinct.
