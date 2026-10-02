from pathlib import Path
from thesys_cli.main import main
from thesys_engine.methodology import load_methodology
from thesys_engine.gates import status
from thesys_engine.agents import GenerationContext
ROOT=Path(__file__).parents[1]

def test_project_and_unit_scopes_are_distinct(tmp_path):
    main(['init','--path',str(tmp_path)])
    main(['intent','create','Build a platform with accounts and analytics.','--path',str(tmp_path)])
    main(['discovery','propose','--agent','mock','--path',str(tmp_path)])
    main(['discovery','accept','--path',str(tmp_path)])
    main(['generate','governance','--agent','mock','--path',str(tmp_path)])
    main(['proposal','accept','governance','--path',str(tmp_path)])
    main(['generate','engineering-units','--agent','mock','--path',str(tmp_path)])
    main(['proposal','accept','engineering-units','--path',str(tmp_path)])
    main(['unit','create','accounts','Accounts','--type','module','--scope','Account management','--path',str(tmp_path)])
    m=load_methodology(ROOT)
    assert status(tmp_path,m,'accounts')['intent']['status']=='approved'
    assert status(tmp_path,m,'accounts')['governance']['status']=='approved'
    assert status(tmp_path,m,'accounts')['context']['status']=='missing'
    assert main(['generate','context','--unit','accounts','--agent','mock','--path',str(tmp_path)])==0
    assert main(['proposal','accept','context','--unit','accounts','--path',str(tmp_path)])==0
    assert status(tmp_path,m,'accounts')['context']['status']=='approved'


def test_context_generation_preserves_unit_metadata(tmp_path):
    main(['init','--path',str(tmp_path)])
    main(['intent','create','Build a platform with accounts and analytics.','--path',str(tmp_path)])
    main(['discovery','propose','--agent','mock','--path',str(tmp_path)])
    main(['discovery','accept','--path',str(tmp_path)])
    main(['generate','governance','--agent','mock','--path',str(tmp_path)])
    main(['proposal','accept','governance','--path',str(tmp_path)])
    main(['generate','engineering-units','--agent','mock','--path',str(tmp_path)])
    main(['proposal','accept','engineering-units','--path',str(tmp_path)])
    main(['unit','create','accounts','Accounts','--type','domain','--scope','Account management','--parent',str(tmp_path.name),'--path',str(tmp_path)])
    assert main(['generate','context','--unit','accounts','--agent','mock','--path',str(tmp_path)])==0
    proposal=(tmp_path/'.thesys/proposals/accounts/context.json').read_text(encoding='utf-8-sig')
    assert 'Unit type: domain' in proposal
    assert f'Parent unit: {tmp_path.name}' in proposal


def test_context_boundary_is_rendered_from_authoritative_unit_metadata():
    from thesys_engine.templates import render_template
    m=load_methodology(ROOT)
    c = GenerationContext("intent", "integracao-dominios", "scope", "pt-BR", {}, {}, {}, "capability", "erp-distribuidora", ())
    from thesys_engine.proposals import _context_boundary_section
    content=render_template(m,'context',{'system-and-unit-boundary':_context_boundary_section(c)},'pt-BR',c.unit)
    assert '- Unidade pai: erp-distribuidora.' in content
    assert '- Tipo de unidade: capability.' in content
    assert 'Não informado' not in content
    assert 'software-system' not in content


def test_project_is_the_canonical_root_and_no_synthetic_unit_is_created(tmp_path):
    from thesys_engine.project import project_key, list_units, work_targets
    assert main(['init', '--path', str(tmp_path)]) == 0
    assert project_key(tmp_path) == tmp_path.name
    assert list_units(tmp_path) == []
    assert work_targets(tmp_path)[0]['key'] == tmp_path.name
    assert work_targets(tmp_path)[0]['type'] == 'project'


def test_legacy_default_root_is_migrated_to_project(tmp_path):
    from thesys_engine.methodology import load_methodology
    from thesys_engine.project import project_info
    from thesys_engine.io import write_text
    import json

    # Simulate the persisted shape emitted by 0.5.0 before reinitialization.
    meta = tmp_path / '.thesys'
    (meta / 'units').mkdir(parents=True)
    (meta / 'proposals' / 'default').mkdir(parents=True)
    write_text(meta / 'project.yaml', '\n'.join([
        'id: PRJ-LEGACY',
        'key: test-project',
        'name: Test Project',
        'template: software-system',
        'kind: software-system',
        'methodology: thesys-core',
        'methodology_version: 0.5.0',
        'status: active',
    ]) + '\n')
    write_text(meta / 'config.yaml', 'language: en-US\nagent_provider: mock\ntemplate: software-system\n')
    write_text(meta / 'registry.json', json.dumps({'artifacts': {}, 'relations': [], 'events': []}) + '\n')
    write_text(meta / 'approvals.json', json.dumps({'approvals': {}}) + '\n')
    write_text(meta / 'units' / 'default.json', json.dumps({
        'key': 'default', 'name': 'Test Project', 'scope': 'System-wide scope',
        'type': 'system', 'parent': None, 'container': False,
    }) + '\n')
    write_text(meta / 'proposals' / 'default' / 'intent.json', json.dumps({
        'stage': 'intent', 'unit': 'default', 'status': 'proposed', 'proposal_id': 'PROP-LEGACY',
        'questions': [], 'content': '# Intent\n\n## Purpose\nLegacy\n'
    }) + '\n')

    assert main(['init', '--path', str(tmp_path)]) == 0
    assert project_info(tmp_path)['key'] == 'test-project'
    assert not (meta / 'units' / 'default.json').exists()
    migrated = meta / 'proposals' / 'test-project' / 'intent.json'
    assert migrated.is_file()
    assert json.loads(migrated.read_text(encoding='utf-8'))['unit'] == 'test-project'
