# Human Guidance

Human Guidance is an optional, durable engineering input for directing AI-assisted proposal generation without making the guidance itself authoritative.

## Why it exists

A proposal can be structurally valid and still move in a direction the human does not want. Instead of treating that situation as a simple rejection, Thesys lets the human add information that should influence the next proposal.

Guidance can be added at any lifecycle stage and can be one of four types:

- **Directive** — a rule or desired direction for the proposal.
- **Review note** — an observation about the current proposal that should be considered during regeneration.
- **Reference** — supporting material that should inform the proposal.
- **Attachment** — a supported UTF-8 text file supplied as reference material.

Guidance is optional. A stage can be proposed and approved without any guidance.

## Propagation

Guidance is forward-propagating. When guidance is added to a stage, it becomes part of the input context for that stage and every downstream stage in the affected scope.

For example:

```text
Context        approved
Requirements   approved
Specification  approved
Architecture   approved
```

Adding guidance to Context makes the current Context baseline stale and causes Requirements, Specification and Architecture to require revalidation/regeneration as appropriate.

Historical artifacts are not deleted. The change is represented through input fingerprints, lifecycle status and the project event history.

## Authority

Human Guidance does not replace an authoritative artifact. Approved engineering artifacts remain the source of truth. If guidance conflicts materially with authoritative context, the AI must surface the conflict rather than silently override the approved decision.

The intended relationship is:

```text
Authoritative engineering context
            ↓
     Human Guidance
            ↓
       AI Proposal
            ↓
      Human Approval
```

## CLI

Add a directive:

```powershell
thesys guidance add requirements directive "Use only BRL in the MVP." --unit financial-records
```

Add a review note:

```powershell
thesys guidance add requirements review-note "Do not introduce audit history in the MVP." --unit financial-records
```

Add a text reference:

```powershell
thesys guidance add requirements reference "Use this as the business reference." --file .\reference.md --unit financial-records
```

List guidance:

```powershell
thesys guidance list
```

The project documentation displays the applicable human guidance alongside the proposal questions and clarification history.
