import json
from thesys_cli.main import main


def test_project_language_controls_generated_content_while_structure_stays_english(tmp_path):
    main(['init','--path',str(tmp_path)])
    main(['config','set','language','pt-BR','--path',str(tmp_path)])
    main(['intent','create','Construir uma plataforma financeira para pequenas empresas.','--path',str(tmp_path)])
    main(['discovery','propose','--agent','mock','--path',str(tmp_path)])
    discovery=json.loads((tmp_path/'.thesys'/'proposals'/'default'/'intent.json').read_text(encoding='utf-8'))
    body=json.loads(discovery['content'])
    assert '# Engineering Context' in body['context']
    assert 'O sistema descrito pelo Intent humano.' in body['context']
    main(['discovery','accept','--path',str(tmp_path)])
    main(['generate','governance','--agent','mock','--path',str(tmp_path)])
    proposal=json.loads((tmp_path/'.thesys'/'proposals'/'default'/'governance.json').read_text(encoding='utf-8'))
    assert '# Governance' in proposal['content']
    assert 'Responsável humano' in proposal['content']


def test_templates_remain_canonical_across_languages(tmp_path):
    from thesys_engine.methodology import load_methodology
    from thesys_engine.templates import load_template
    m=load_methodology(__import__('pathlib').Path(__file__).parents[1])
    assert load_template(m,'context','pt-BR') == load_template(m,'context','en-US')


def test_project_language_falls_back_to_methodology_language(tmp_path):
    main(['init','--path',str(tmp_path)])
    from thesys_engine.project import project_language
    assert project_language(tmp_path,'en-US') == 'en-US'
