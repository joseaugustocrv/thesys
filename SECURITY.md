# Security

## Principles

Thesys treats AI output as untrusted input until a human accepts it as an
authoritative artifact. Generated code is also treated as untrusted and must
pass project verification before release.

API keys and credentials must be supplied through environment variables or
local secret management and must not be committed to the repository.

Thesys does not execute generated code automatically. Implementation writes
proposed files into the project and leaves execution and deployment to the
project's normal verification process.
