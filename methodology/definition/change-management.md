# Change management

Thesys treats change as a normal part of engineering rather than an exception.

## Upstream change

When an authoritative artifact changes after approval:

1. the stored approval hash no longer matches;
2. the artifact becomes stale;
3. dependent stages require revalidation;
4. questions and clarification decisions are recorded when needed;
5. affected proposals are regenerated from the new authoritative context.

## Downstream discovery

If implementation, verification, or convergence discovers information that
changes an upstream decision, the team must not silently patch only the
implementation. The question is recorded, the upstream artifact is updated,
and affected downstream artifacts are revalidated.

## Traceability requirement

Every material change should be explainable through the chain:

```text
Change → Question → Decision → Updated artifact → Impact → Revalidation
```
