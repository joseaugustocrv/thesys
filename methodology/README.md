# Thesys methodology

This directory is the source of the executable methodology used by the Thesys
runtime.

The methodology is intentionally part of the product. Changes here can alter
lifecycle behavior, templates, gates, and agent instructions without requiring
changes to the generic engine.

## Contents

- `definition/` contains executable lifecycle definitions.
- `templates/` contains authoritative artifact templates.
- `prompts/` contains methodology-owned agent instructions.

## Template and localization contract

Artifact templates define the document structure. Agents return section content
against that structure rather than generating headings or copying template
instructions. Human-facing structural labels are localized through the
methodology localization resources. Generated natural language is validated
against the configured language; invalid output is rejected rather than
rewritten by post-processing substitutions.
