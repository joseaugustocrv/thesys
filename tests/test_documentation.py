import json
from pathlib import Path
from thesys_cli.main import main
from thesys_engine.documentation import _markdown


def test_docs_build_generates_static_navigation(tmp_path):
    main(['init','--path',str(tmp_path)])
    main(['intent','create','Build a documentation test project.','--path',str(tmp_path)])
    main(['discovery','propose','--agent','mock','--path',str(tmp_path)])
    main(['discovery','accept','--path',str(tmp_path)])
    main(['generate','governance','--agent','mock','--path',str(tmp_path)])
    main(['proposal','accept','governance','--path',str(tmp_path)])
    main(['docs','build','--path',str(tmp_path)])
    out=tmp_path/'.thesys'/'docs'
    assert (out/'index.html').is_file()
    assert (out/'styles.css').is_file()
    manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8-sig'))
    assert manifest['artifact_count'] >= 2
    html=(out/'index.html').read_text(encoding='utf-8-sig')
    assert 'Engineering Context' in html
    assert 'System Architecture Integration' in html
    assert 'Related artifacts' in html
    assert 'Questions & answers' in html
    assert 'Architecture & Design' in html
    assert 'const LIFECYCLE' in html
    assert 'Supporting artifacts' in html
    assert 'Pending' in html
    assert 'generated=' not in html
    assert 'lifecycle stages approved' in html
    assert 'lifecycle stages completed' not in html
    assert 'data:image/svg+xml;base64,' in html
    assert 'Thesys logo' in html
    assert 'data:image/svg+xml;base64,PHN2Zy' in html


def test_markdown_tables_render_as_html_tables():
    rendered=_markdown(
        "| Dependency | Owner | Constraint |\n"
        "|---|:---:|---:|\n"
        "| PostgreSQL | Platform | Version 16 |\n"
    )
    assert '<table>' in rendered
    assert '<thead>' in rendered
    assert '<tbody>' in rendered
    assert '<th scope="col">Dependency</th>' in rendered
    assert 'style="text-align:center"' in rendered
    assert 'style="text-align:right"' in rendered
    assert '| Dependency | Owner | Constraint |' not in rendered



def test_documentation_uses_runtime_statuses_without_artifact_position_inference(tmp_path):
    main(['init','--path',str(tmp_path)])
    main(['intent','create','Build a documentation runtime-state test project.','--path',str(tmp_path)])
    main(['docs','build','--path',str(tmp_path)])
    html=(tmp_path/'.thesys/docs/index.html').read_text(encoding='utf-8-sig')
    assert 'const LIFECYCLE_STATUS' in html
    assert "case 'blocked': return 'blocked';" in html
    assert "case 'needs_revalidation':" in html
    assert "case 'partial': return 'in-progress';" in html
    assert "return previous ? 'upcoming' : 'not-generated';" not in html

def test_docs_build_structures_evidence_and_searches_content(tmp_path):
    main(['init','--path',str(tmp_path)])
    evidence_dir=tmp_path/'.thesys'/'evidence'
    evidence_dir.mkdir(parents=True,exist_ok=True)
    evidence=(
        '{\n'
        '  "id": "EVD-001",\n'
        '  "type": "validation",\n'
        '  "subject": "LGPD validation",\n'
        '  "result": "Validation completed",\n'
        '  "related_artifacts": ["REQ-001"]\n'
        '}\n'
    )
    (evidence_dir/'EVD-001.json').write_text(evidence,encoding='utf-8')
    registry={
        'artifacts': {
            'EVD-001': {
                'id':'EVD-001','type':'EVD','path':str(evidence_dir/'EVD-001.json'),
                'unit':'system','status':'authoritative','authority':'system'
            }
        },
        'relations': [], 'events': []
    }
    (tmp_path/'.thesys'/'registry.json').write_text(__import__('json').dumps(registry),encoding='utf-8')
    main(['docs','build','--path',str(tmp_path)])
    html=(tmp_path/'.thesys'/'docs'/'index.html').read_text(encoding='utf-8-sig')
    assert 'evidence-card' in html
    assert 'Subject' in html
    assert 'LGPD validation' in html
    assert '${x.id} ${x.title} ${x.path} ${x.html}' in html


def test_docs_include_current_non_authoritative_proposals_and_clarification_history(tmp_path):
    main(['init','--path',str(tmp_path)])
    main(['config','set','agent_provider','mock','--path',str(tmp_path)])
    main(['intent','create','Build a platform [[QUESTION:policy]]','--path',str(tmp_path)])
    main(['next','--path',str(tmp_path)])
    answer='A organização exige aprovação antes de alterações relevantes.'
    main(['question','answer','QST-001',answer,'--path',str(tmp_path)])
    main(['next','--path',str(tmp_path)])
    html=(tmp_path/'.thesys/docs/index.html').read_text(encoding='utf-8-sig')
    assert 'Proposal ·' in html or 'Proposta' in html
    assert 'non-authoritative' in html
    assert 'Clarification history' in html
    assert answer in html


def test_docs_group_lifecycle_by_phase_and_keep_project_intent_after_units(tmp_path):
    main(['init','--path',str(tmp_path)])
    main(['config','set','agent_provider','mock','--path',str(tmp_path)])
    main(['intent','create','Build an ERP for a distributor.','--path',str(tmp_path)])
    main(['next','--path',str(tmp_path)])
    main(['discovery','accept','--path',str(tmp_path)])
    main(['next','--path',str(tmp_path)])
    main(['proposal','accept','governance','--path',str(tmp_path)])
    main(['next','--path',str(tmp_path)])

    html=(tmp_path/'.thesys/docs/index.html').read_text(encoding='utf-8-sig')
    manifest=json.loads((tmp_path/'.thesys/docs/manifest.json').read_text(encoding='utf-8-sig'))
    assert 'nav-phase' in html
    assert 'nav-phase-items' in html
    assert '<small>discovery-foundation</small>' not in html
    assert 'Discovery & Foundation' in html
    assert any(item['type'] == 'INT' for item in manifest['artifacts'])
    assert any(item['type'] == 'GOV' for item in manifest['artifacts'])


def test_approved_proposals_are_hidden_from_primary_navigation(tmp_path):
    main(['init','--path',str(tmp_path)])
    main(['intent','create','Build a documentation test project.','--path',str(tmp_path)])
    main(['discovery','propose','--agent','mock','--path',str(tmp_path)])
    main(['discovery','accept','--path',str(tmp_path)])
    main(['generate','governance','--agent','mock','--path',str(tmp_path)])
    main(['proposal','accept','governance','--path',str(tmp_path)])
    main(['docs','build','--path',str(tmp_path)])
    html=(tmp_path/'.thesys/docs/index.html').read_text(encoding='utf-8-sig')
    assert 'Proposta · Governance' not in html
    assert 'Governance & Constitution' in html

def test_documentation_contains_phase_status_classes(tmp_path):
    main(['init','--path',str(tmp_path)])
    main(['intent','create','Build a documentation test project.','--path',str(tmp_path)])
    main(['discovery','propose','--agent','mock','--path',str(tmp_path)])
    main(['docs','build','--path',str(tmp_path)])
    html=(tmp_path/'.thesys/docs/index.html').read_text(encoding='utf-8-sig')
    assert 'nav-stage' in html
    assert 'function itemState' in html
    assert 'LIFECYCLE_SCOPES' in html
    assert 'LIFECYCLE_PHASES' in html
    assert 'LIFECYCLE_STATUS' in html
    assert 'UNIT_KEYS' in html


def test_docs_distinguish_architecture_and_system_architecture_with_shared_prefix(tmp_path):
    from thesys_engine.documentation import _artifact_items
    main(['init','--path',str(tmp_path)])
    arch=tmp_path/'engineering/architecture/compras/architecture.md'
    sysarch=tmp_path/'engineering/architecture/system-architecture.md'
    arch.parent.mkdir(parents=True,exist_ok=True)
    arch.write_text('# Arquitetura\n',encoding='utf-8')
    sysarch.write_text('# Arquitetura do Sistema\n',encoding='utf-8')
    registry={
        'artifacts': {
            'ARC-001': {'id':'ARC-001','type':'ARC','path':str(arch),'unit':'compras','status':'authoritative','authority':'human'},
            'ARC-002': {'id':'ARC-002','type':'ARC','path':str(sysarch),'unit':tmp_path.name,'status':'authoritative','authority':'human'},
        },
        'relations': [], 'events': []
    }
    (tmp_path/'.thesys/registry.json').write_text(json.dumps(registry),encoding='utf-8')
    items=_artifact_items(tmp_path)
    by_id={item['id']:item for item in items}
    assert by_id['ARC-001']['stage']=='architecture'
    assert by_id['ARC-002']['stage']=='system-architecture'


def test_docs_do_not_collide_stages_with_shared_artifact_prefix(tmp_path):
    main(['init','--path',str(tmp_path)])
    from thesys_engine.registry import register_artifact
    import json
    arch=tmp_path/'engineering/architecture/compras/architecture.md'
    sysarch=tmp_path/'engineering/architecture/system-architecture.md'
    arch.parent.mkdir(parents=True,exist_ok=True)
    arch.write_text('# Arquitetura e Design\n',encoding='utf8')
    sysarch.write_text('# Integração da Arquitetura do Sistema\n',encoding='utf8')
    registry={'artifacts':{},'relations':[],'events':[]}
    registry['artifacts']={
        'ARC-001': {'id':'ARC-001','type':'ARC','path':str(arch),'unit':'compras','status':'authoritative','authority':'human'},
        'ARC-002': {'id':'ARC-002','type':'ARC','path':str(sysarch),'unit':tmp_path.name,'status':'authoritative','authority':'human'},
    }
    (tmp_path/'.thesys/registry.json').write_text(json.dumps(registry),encoding='utf8')
    main(['config','set','language','pt-BR','--path',str(tmp_path)])
    main(['docs','build','--path',str(tmp_path)])
    html=(tmp_path/'.thesys/docs/index.html').read_text(encoding='utf-8-sig')
    manifest=json.loads((tmp_path/'.thesys/docs/manifest.json').read_text(encoding='utf-8-sig'))
    by_id={x['id']:x for x in manifest['artifacts']}
    assert by_id['ARC-001']['stage']=='architecture'
    assert by_id['ARC-002']['stage']=='system-architecture'
    assert "stageItems(stageKey)" in html
    assert "stageItems(key)" in html
    assert "LIFECYCLE_SCOPES[stageKey]" in html
    assert 'DOCUMENTAÇÃO' in html
    assert 'Pesquisar artefatos' in html


def test_docs_localize_lifecycle_shell_for_project_language(tmp_path):
    main(['init','--path',str(tmp_path)])
    main(['config','set','language','pt-BR','--path',str(tmp_path)])
    main(['intent','create','Criar um sistema.','--path',str(tmp_path)])
    main(['docs','build','--path',str(tmp_path)])
    html=(tmp_path/'.thesys/docs/index.html').read_text(encoding='utf-8-sig')
    assert '<html lang="pt-BR">' in html
    assert 'DOCUMENTAÇÃO' in html
    assert 'Pesquisar artefatos' in html
    assert 'Arquitetura e Design' in html
    assert 'Integração da Arquitetura do Sistema' in html
    assert 'Perguntas e respostas' in html


def test_authoritative_artifact_keeps_clarification_history_after_acceptance(tmp_path):
    main(['init','--path',str(tmp_path)])
    main(['config','set','agent_provider','mock','--path',str(tmp_path)])
    main(['intent','create','Build a platform [[QUESTION:policy]]','--path',str(tmp_path)])
    main(['next','--path',str(tmp_path)])
    main(['question','answer','QST-001','A human decision recorded before approval.','--path',str(tmp_path)])
    main(['next','--path',str(tmp_path)])
    main(['discovery','accept','--path',str(tmp_path)])
    html=(tmp_path/'.thesys/docs/index.html').read_text(encoding='utf-8-sig')
    assert 'A human decision recorded before approval.' in html
    assert 'QST-001' in html


def test_presentation_documentation_omits_project_content(tmp_path):
    main(['init','--path',str(tmp_path)])
    main(['config','set','agent_provider','mock','--path',str(tmp_path)])
    main(['intent','create','Confidential customer pricing and strategic acquisition details.','--path',str(tmp_path)])
    main(['docs','build','--presentation','--path',str(tmp_path)])
    html=(tmp_path/'.thesys/docs/index.html').read_text(encoding='utf-8-sig')
    assert 'Confidential customer pricing' not in html
    assert 'strategic acquisition' not in html
    assert 'Thesys Engineering Overview' in html
    assert 'DISCOVERY & FOUNDATION' not in html or 'Discovery & Foundation' in html


def test_docs_phase_groups_expose_status_and_collapse_affordance(tmp_path):
    from thesys_cli.main import main
    main(['init','--path',str(tmp_path)])
    main(['intent','create','Build a documentation test project.','--path',str(tmp_path)])
    main(['docs','build','--path',str(tmp_path)])
    html=(tmp_path/'.thesys/docs/index.html').read_text(encoding='utf-8-sig')
    assert 'phase-status-dot' in html
    assert 'nav-chevron' in html
    assert 'nav-phase' in html




def test_documentation_presents_names_before_ids_and_guidance_ids(tmp_path):
    from thesys_engine.guidance import add_guidance
    from thesys_engine.methodology import load_methodology
    main(['init','--path',str(tmp_path)])
    main(['config','set','language','pt-BR','--path',str(tmp_path)])
    main(['config','set','agent_provider','mock','--path',str(tmp_path)])
    main(['intent','create','Criar um sistema de testes de documentação.','--path',str(tmp_path)])
    main(['next','--path',str(tmp_path)])
    main(['discovery','accept','--path',str(tmp_path)])
    main(['next','--path',str(tmp_path)])
    main(['proposal','accept','governance','--path',str(tmp_path)])
    m=load_methodology(Path(__file__).parents[1])
    add_guidance(tmp_path,'governance',tmp_path.name,'directive','Preserve the original boundary.','Limite de governança',methodology=m)
    main(['docs','build','--path',str(tmp_path)])
    html=(tmp_path/'.thesys/docs/index.html').read_text(encoding='utf-8-sig')
    assert 'GUD-001' in html
    assert 'Limite de governança' in html
    assert 'x.title} · ${x.id}' in html
    assert '<strong>${esc(r.title)}</strong><span>${esc(id)}</span>' in html
    assert "g.id||''" in html
    assert '${esc(g.title||g.type)}' in html

def test_presentation_docs_do_not_expose_human_guidance(tmp_path):
    from thesys_cli.main import main
    from thesys_engine.guidance import add_guidance
    from thesys_engine.methodology import load_methodology
    main(['init','--path',str(tmp_path)])
    m=load_methodology(Path(__file__).parents[1])
    add_guidance(tmp_path,'intent',tmp_path.name,'directive','Internal project direction: do not expose this.','Internal guidance',methodology=m)
    main(['docs','build','--presentation','--path',str(tmp_path)])
    html=(tmp_path/'.thesys/docs/index.html').read_text(encoding='utf-8-sig')
    assert 'Internal project direction: do not expose this.' not in html
    assert 'Internal guidance' not in html
