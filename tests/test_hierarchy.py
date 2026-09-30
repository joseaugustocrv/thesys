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
    main(['unit','create','accounts','Accounts','--type','domain','--scope','Account management','--parent','default','--path',str(tmp_path)])
    assert main(['generate','context','--unit','accounts','--agent','mock','--path',str(tmp_path)])==0
    proposal=(tmp_path/'.thesys/proposals/accounts/context.json').read_text(encoding='utf-8-sig')
    assert 'Unit type: domain' in proposal
    assert 'Parent unit: default' in proposal


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
