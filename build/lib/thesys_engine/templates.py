from .io import read_text

def load_template(methodology, stage_id, language=None):
    stage=methodology.stage(stage_id)
    if not stage.template: raise ValueError(f"Stage '{stage_id}' has no template.")
    path=methodology.root/stage.template
    return read_text(path)
