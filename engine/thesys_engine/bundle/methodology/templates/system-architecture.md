# System Architecture Integration

This artifact is the integrated architectural view of the project. It synthesizes
approved Unit architectures; it must not silently replace or contradict them.

## System context

Describe the system as a whole and its external actors, systems and boundaries.

## Engineering Unit map

| Unit | Responsibility | Parent | Dependencies |
| --- | --- | --- | --- |
| [UNIT] | [Responsibility] | [Parent] | [Dependencies] |

## Cross-Unit boundaries

Describe the responsibilities and boundaries between Engineering Units.

## Cross-Unit interfaces

| Source Unit | Interface / Interaction | Target Unit | Contract / Constraint |
| --- | --- | --- | --- |
| [UNIT] | [Interface] | [UNIT] | [Contract] |

## Data and control flows

Describe important flows that cross Unit boundaries.

## Shared components and concerns

Describe shared infrastructure, data, security, quality and operational concerns.

## Deployment and runtime topology

Describe the integrated deployment and runtime topology where it is known.

## System-level architecture decisions

Record decisions that affect more than one Unit or establish system-wide constraints.

## Unit architecture consistency

Identify important consistency constraints, dependencies, conflicts or unresolved
integration concerns discovered while synthesizing the approved Unit architectures.

## Traceability

| Unit / Requirement | System Component or Boundary | Verification |
| --- | --- | --- |
| [Reference] | [Component / Boundary] | [Verification] |

## Architecture status

**Status:** Draft
