# AI and Human Authority

Thesys treats AI as an engineering participant, not as an autonomous authority.

## Authority model

```text
Authoritative Context
       ↓
AI Analysis
       ↓
Proposal + Questions
       ↓
Human Answers
       ↓
Revised Proposal
       ↓
Human Approval
       ↓
Authoritative Artifact
```

An AI output cannot silently become an input to a later stage.

## Questions are first-class

When material information is missing, the AI must ask rather than invent. Questions have identifiers, rationale and blocking status. Answering a question invalidates the proposal that depended on the unanswered state; the AI must regenerate it.

## Implementation

Code is treated as a proposal. The runtime validates generated paths and applies code only after the human accepts the implementation proposal. Generated code is never executed implicitly.

## Verification

Execution results are produced by the runtime and stored as evidence. AI may interpret those results and propose a verification artifact, but it cannot fabricate test execution or evidence.
