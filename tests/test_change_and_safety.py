from pathlib import Path
from thesys_cli.main import main
from thesys_engine.methodology import load_methodology
from thesys_engine.gates import status
from thesys_engine.errors import ProjectError
import pytest
ROOT=Path(__file__).parents[1]

def complete_to_implementation(tmp_path):
    for args in [
        ['init'],['intent','create','Build a system.'],['discovery','propose','--agent','mock'],['discovery','accept'],['generate','governance','--agent','mock'],['proposal','accept','governance'],['generate','engineering-units','--agent','mock'],['proposal','accept','engineering-units'],['generate','context','--agent','mock'],['proposal','accept','context']]:
        assert main(args+['--path',str(tmp_path)])==0
    for stage in ['requirements','clarification','specification','acceptance','architecture','system-architecture','quality','security','risk','plan','tasks']:
        assert main(['generate',stage,'--agent','mock','--path',str(tmp_path)])==0
        assert main(['proposal','accept',stage,'--path',str(tmp_path)])==0

def test_upstream_change_invalidates_downstream(tmp_path):
    complete_to_implementation(tmp_path)
    main(['implementation','propose','--agent','mock','--path',str(tmp_path)])
    main(['implementation','accept','--path',str(tmp_path)])
    p=tmp_path/f'engineering/requirements/{tmp_path.name}/requirements.md'; p.write_text(p.read_text(encoding='utf-8-sig')+'\n## Change\n\nNew requirement.\n',encoding='utf8')
    st=status(tmp_path,load_methodology(ROOT))
    assert st['requirements']['status']=='needs_revalidation'
    assert st['architecture']['status']=='needs_revalidation'
    assert st['implementation']['status']=='blocked'

def test_implementation_rejects_unsafe_paths(tmp_path):
    complete_to_implementation(tmp_path)
    assert main(['implementation','propose','--agent','mock','--path',str(tmp_path)])==0
    import json
    p=tmp_path / '.thesys' / 'proposals' / tmp_path.name / 'implementation.json'
    data=json.loads(p.read_text(encoding='utf-8-sig')); body=json.loads(data['content']); body['files']={'../escape.py':'x'}; data['content']=json.dumps(body); p.write_text(json.dumps(data),encoding='utf8')
    with pytest.raises(ProjectError):
        main(['implementation','accept','--path',str(tmp_path)])

def test_implementation_accepts_explicit_root_files_and_list_payload(tmp_path):
    complete_to_implementation(tmp_path)
    assert main(['implementation','propose','--agent','mock','--path',str(tmp_path)])==0
    import json
    proposal_path=tmp_path / '.thesys' / 'proposals' / tmp_path.name / 'implementation.json'
    data=json.loads(proposal_path.read_text(encoding='utf-8-sig'))
    body=json.loads(data['content'])
    body['files']=[
        {'path':'index.html','content':'<!doctype html>\n'},
        {'path':'src/main.py','content':'print(\"ok\")\n'},
    ]
    data['content']=json.dumps(body)
    proposal_path.write_text(json.dumps(data),encoding='utf8')
    assert main(['implementation','accept','--path',str(tmp_path)])==0
    assert (tmp_path/'index.html').is_file()
    assert (tmp_path/'src/main.py').is_file()

