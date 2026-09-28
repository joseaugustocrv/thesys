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
    manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['artifact_count'] >= 2
    html=(out/'index.html').read_text(encoding='utf-8')
    assert 'Engineering Context' in html
    assert 'System Architecture Integration' in html
    assert 'Related artifacts' in html
    assert 'Questions & answers' in html
    assert 'const LIFECYCLE' in html
    assert 'Supporting artifacts' in html
    assert 'Not generated' in html
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
    html=(tmp_path/'.thesys'/'docs'/'index.html').read_text(encoding='utf-8')
    assert 'evidence-card' in html
    assert 'Subject' in html
    assert 'LGPD validation' in html
    assert '${x.id} ${x.title} ${x.path} ${x.html}' in html
