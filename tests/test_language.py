import json
from thesys_cli.main import main


def test_project_language_controls_generated_content_while_structure_stays_english(tmp_path):
    main(['init','--path',str(tmp_path)])
    main(['config','set','language','pt-BR','--path',str(tmp_path)])
    main(['intent','create','Construir uma plataforma financeira para pequenas empresas.','--path',str(tmp_path)])
    main(['discovery','propose','--agent','mock','--path',str(tmp_path)])
    discovery=json.loads((tmp_path/'.thesys'/'proposals'/'default'/'intent.json').read_text(encoding='utf-8-sig'))
    assert '# Intenção' in discovery['content'] or '# Intent' in discovery['content']
    assert 'discovery_context' in discovery
    assert '# Contexto de Engenharia' in discovery['discovery_context']
    main(['discovery','accept','--path',str(tmp_path)])
    main(['generate','governance','--agent','mock','--path',str(tmp_path)])
    proposal=json.loads((tmp_path/'.thesys'/'proposals'/'default'/'governance.json').read_text(encoding='utf-8-sig'))
    assert '# Governança' in proposal['content']
    assert '## Propósito' in proposal['content']
    assert 'Conteúdo proposto' in proposal['content']


def test_templates_define_structure_and_localize_headings(tmp_path):
    from thesys_engine.methodology import load_methodology
    from thesys_engine.templates import template_contract, render_template
    m=load_methodology(__import__('pathlib').Path(__file__).parents[1])
    contract=template_contract(m,'context')
    assert 'system-and-unit-boundary' in contract.section_ids
    pt=render_template(m,'context',{'system-and-unit-boundary':'conteúdo'},'pt-BR','sales')
    en=render_template(m,'context',{'system-and-unit-boundary':'content'},'en-US','sales')
    assert '## Limites do sistema e da unidade' in pt
    assert '## System and unit boundary' in en
    assert 'conteúdo' in pt and 'content' in en


def test_project_language_falls_back_to_methodology_language(tmp_path):
    main(['init','--path',str(tmp_path)])
    from thesys_engine.project import project_language
    assert project_language(tmp_path,'en-US') == 'en-US'


