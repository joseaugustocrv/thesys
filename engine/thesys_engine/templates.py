from .template_contract import load_contract, load_localization, render_sections, contract_schema
from .io import read_text


def load_template(methodology, stage_id, language=None):
    """Return the canonical structural template.

    Templates are structural contracts. They are not translated or rewritten
    by the model. Use ``load_contract`` and ``render_sections`` for generation.
    """
    stage = methodology.stage(stage_id)
    if not stage.template:
        raise ValueError(f"Stage '{stage_id}' has no template.")
    return read_text(methodology.root / stage.template)


def template_contract(methodology, stage_id):
    return load_contract(methodology, stage_id)


def template_schema(methodology, stage_id):
    return contract_schema(load_contract(methodology, stage_id))


def render_template(methodology, stage_id, sections, language, unit_key="default"):
    contract = load_contract(methodology, stage_id)
    localization = load_localization(methodology, language)
    return render_sections(contract, sections, localization, unit_key)
