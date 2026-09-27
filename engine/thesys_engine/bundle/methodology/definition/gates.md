# Gates

Gates are explicit controls defined by the methodology and evaluated by the
runtime.

## Human validation gate

A stage marked `approval: required` cannot provide authoritative input to a
dependent stage until its current artifact is approved.

## Dependency gate

A stage is actionable only when all required upstream stages satisfy their
current gate state.

## Blocking-question gate

A material unresolved question blocks the affected decision until the question
is resolved or explicitly dispositioned by the methodology.

## Implementation gate

Implementation is available only after the approved context required by the
methodology is complete. The runtime may generate files, but it does not claim
that the generated software is verified.

## Verification gate

Verification produces evidence. Passing evidence does not automatically make
its artifact authoritative; the verification artifact still follows the human
approval model.

## Release gate

Release readiness requires successful verification, convergence, traceability,
and no unresolved blocking findings.
