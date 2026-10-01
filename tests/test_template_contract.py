from pathlib import Path
from thesys_engine.methodology import load_methodology
from thesys_engine.templates import template_contract, render_template

ROOT = Path(__file__).parents[1]


def test_all_lifecycle_templates_have_unique_section_ids():
    m = load_methodology(ROOT)
    for stage in m.stages:
        if not stage.template:
            continue
        contract = template_contract(m, stage.id)
        assert len(contract.section_ids) == len(set(contract.section_ids)), stage.id


def test_pt_br_rendering_owns_document_structure():
    m = load_methodology(ROOT)
    contract = template_contract(m, 'intent')
    sections = {section.id: 'conteúdo' for section in contract.sections}
    rendered = render_template(m, 'intent', sections, 'pt-BR')
    assert '# Intenção' in rendered
    assert '## Propósito' in rendered
    assert '## Usuários e partes interessadas' in rendered
    assert '## Intent' not in rendered
    req_contract = template_contract(m, 'requirements')
    req_sections = {section.id: 'conteúdo' for section in req_contract.sections}
    req_rendered = render_template(m, 'requirements', req_sections, 'pt-BR', 'test-project')
    assert 'REQ-001 — Requisito funcional' in req_rendered
    assert '[Título do requisito]' not in req_rendered


def test_generated_content_is_not_rewritten_to_change_language():
    from thesys_engine.proposals import _validate_generated_content
    bad = '# Intenção\n\n## Propósito\n\nThe system must comply.'
    try:
        _validate_generated_content(bad, 'pt-BR')
    except Exception as exc:
        assert 'normative terminology' in str(exc)
    else:
        raise AssertionError('Invalid language output must be rejected, not rewritten.')


def test_engineering_templates_do_not_embed_questions():
    m = load_methodology(ROOT)
    for stage_id in ("intent", "context", "requirements", "specification", "clarification"):
        contract = template_contract(m, stage_id)
        headings = {section.heading.casefold() for section in contract.sections}
        assert not ({"open questions", "questions", "questões em aberto"} & headings), stage_id
        rendered = render_template(m, stage_id, {section.id: "conteúdo" for section in contract.sections}, "pt-BR", "test-project")
        assert "QST-001" not in rendered, stage_id

def test_generated_content_rejects_question_sections_ids_and_placeholders():
    from thesys_engine.proposals import _validate_generated_content
    bad_samples = (
        "# Requisitos\n\n## Questões em aberto\n\nNenhuma.",
        "# Requisitos\n\nREQ-001 atende QST-020.",
        "# Requisitos\n\n[Título do requisito]",
    )
    for bad in bad_samples:
        try:
            _validate_generated_content(bad, "pt-BR", ("[Título do requisito]",))
        except Exception:
            pass
        else:
            raise AssertionError("Document contract violation was not rejected")
