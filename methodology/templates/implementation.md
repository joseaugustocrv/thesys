# Implementation

Implementation is a controlled action defined by the methodology.

## Preconditions

The runtime must have approved intent, requirements, specification,
architecture, plan, and tasks for the target unit.

## Output

The implementation agent returns a structured set of project-relative files.
The runtime validates paths, writes files only under methodology-defined allowed roots
or explicitly allowed root-level files, and records an implementation manifest.

## Safety

Generated code is not executed automatically. Verification is a separate
lifecycle stage.
