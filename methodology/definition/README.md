# Methodology definition

`lifecycle.md` is the canonical executable definition for the MVP.

Its YAML front matter is parsed by the runtime. The Markdown body explains the
rules to humans and should stay synchronized with the structured definition.

The lifecycle definition is hierarchical. Phases are organizational groupings; stages are the executable gates with dependencies, scope, action and approval semantics. Engineering Units is a first-class stage and is not implemented as a hidden orchestration transition.
