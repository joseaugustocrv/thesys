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

When material information is missing, the AI must ask rather than invent. Questions have rationale and blocking status; Thesys assigns their canonical identifiers. Answering a question invalidates the proposal that depended on the unanswered state; the AI must regenerate it.

## Implementation

Code is treated as a proposal. The runtime validates generated paths and applies code only after the human accepts the implementation proposal. Generated code is never executed implicitly.

## Verification

Execution results are produced by the runtime and stored as evidence. AI may interpret those results and propose a verification artifact, but it cannot fabricate test execution or evidence.

## Structured artifact generation

Lifecycle templates are structural contracts. The AI does not generate Markdown headings or rewrite a canonical template. It returns content keyed by the template's section identifiers; Thesys renders the document structure and localized headings deterministically.

Localization is therefore a structural concern, not a post-processing pass over generated prose. Generated content that violates the configured language contract is rejected rather than repaired by lexical substitutions.

## Clarification-question identity

Clarification-question identity is owned by the Thesys runtime. AI agents return
question text, rationale and blocking status, but never assign question IDs.
Thesys allocates project-wide canonical IDs in the `QST-NNN` format and preserves
an existing ID when a regenerated proposal represents the same unresolved
decision. Human answers are keyed by those canonical IDs and are carried into
clarification history during regeneration.
