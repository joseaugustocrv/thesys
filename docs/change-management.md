# Change management

Change is a normal property of software engineering. The objective is not to eliminate change, but to prevent uncontrolled propagation of change.

## Source before derivation

The central principle is:

> Change the source of intent before changing derived artifacts.

When a meaningful requirement changes, the team first determines what the change affects before editing downstream specifications, architecture, tasks, implementation or verification.

## Impact analysis

A meaningful change can affect:

- requirements and acceptance criteria;
- specifications and behavior;
- architecture decisions and interfaces;
- quality and security controls;
- dependencies and affected engineering units;
- implementation tasks;
- tests and verification evidence;
- release readiness;
- operational procedures.

Impact analysis should distinguish what remains valid from what requires review, regeneration, implementation or re-verification.

## Revalidation

An approval represents a particular state of engineering knowledge. When the authoritative content changes, downstream conclusions may no longer be valid. A controlled lifecycle therefore revalidates affected work instead of silently carrying old decisions into a new state.

## Change during operation

Customer feedback, incidents, security findings, performance constraints and technical discoveries can all initiate engineering change. Operational learning becomes part of the engineering lifecycle rather than a separate stream of undocumented work.
