# Contributing

Changes to Thesys should preserve the separation between methodology and
runtime. Prefer changing methodology definitions and templates when behavior
is genuinely methodological; change the engine only when the generic runtime
capability is missing.

Before submitting a change, run:

```text
python -m pytest
python scripts/check_links.py
python scripts/check_repository.py
```

Documentation changes must also pass the repository Markdown workflow.
