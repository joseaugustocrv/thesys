import json
from pathlib import Path
from thesys_cli.main import main


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
    assert 'Related artifacts' in html
    assert 'Questions & answers' in html
    assert 'const LIFECYCLE' in html
    assert 'Supporting artifacts' in html
    assert 'Not generated' in html
