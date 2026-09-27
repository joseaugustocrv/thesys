# Verification

Verification provides evidence that an implemented result satisfies approved engineering intent and relevant quality and security expectations.

## Verification is broader than testing

Testing is an important technique, but verification can also include:

- static analysis;
- integration checks;
- interface validation;
- security testing;
- performance analysis;
- configuration verification;
- migration validation;
- manual inspection;
- operational readiness checks.

The appropriate combination depends on risk and context.

## Evidence

A verification activity should leave enough evidence to understand:

- what was verified;
- which expectation was used;
- the relevant scope or environment;
- which method was applied;
- what result was observed;
- which deviations remain.

## Failures are engineering information

A failed verification should feed diagnosis and controlled change. Sometimes the implementation is wrong; sometimes the specification is incomplete; sometimes a requirement or assumption has changed. The lifecycle should make those distinctions visible.

## Verification and release

Verification contributes evidence to the release decision. Passing tests alone does not establish readiness when important security, operational, risk or acceptance concerns remain unresolved.
