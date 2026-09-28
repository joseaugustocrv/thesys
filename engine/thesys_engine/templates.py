from .io import read_text

def load_template(methodology, stage_id, language=None):
    """Load the canonical English structural template for a lifecycle stage.

    ``language`` is accepted for API compatibility and future template variants,
    but canonical Thesys templates intentionally keep their structural labels in
    English. The configured project language is applied to generated content by
    the agent instead of duplicating templates per locale.
    """
    stage=methodology.stage(stage_id)
    if not stage.template: raise ValueError(f"Stage '{stage_id}' has no template.")
    path=methodology.root/stage.template
    return read_text(path)
