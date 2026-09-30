import json
from pathlib import Path
import pytest

from thesys_cli.main import main
from thesys_engine.errors import ProjectError
from thesys_engine.registry import get


def cli(workspace, *args):
    return main([*args, '--path', str(workspace)])


def test_project_creation_is_confined_to_thesys_projects_workspace(tmp_path):
    workspace = tmp_path.parent
    assert cli(workspace, 'project', 'create', 'finance-platform') == 0
    assert (workspace / 'finance-platform' / '.thesys/project.yaml').is_file()
    assert not (tmp_path / 'finance-platform').exists()

    outside = tmp_path.parent.parent / 'outside'
    outside.mkdir(exist_ok=True)
    with pytest.raises(ProjectError):
        cli(outside, 'init')


def test_registry_uses_methodology_artifact_prefixes(tmp_path):
    assert cli(tmp_path, 'init') == 0
    assert cli(tmp_path, 'intent', 'create', 'Build a system.') == 0
    assert cli(tmp_path, 'discovery', 'propose', '--agent', 'mock') == 0
    assert cli(tmp_path, 'discovery', 'accept') == 0
    assert cli(tmp_path, 'generate', 'governance', '--agent', 'mock') == 0
    assert cli(tmp_path, 'proposal', 'accept', 'governance') == 0
    assert cli(tmp_path, 'generate', 'context', '--agent', 'mock') == 0
    assert cli(tmp_path, 'proposal', 'accept', 'context') == 0
    for stage in ['requirements', 'clarification', 'specification', 'acceptance', 'architecture']:
        assert cli(tmp_path, 'generate', stage, '--agent', 'mock') == 0
        assert cli(tmp_path, 'proposal', 'accept', stage) == 0

    registry = get(tmp_path)
    ids = set(registry['artifacts'])
    assert 'INT-001' in ids
    assert 'CTX-001' in ids
    assert 'GOV-001' in ids
    assert 'REQ-001' in ids
    assert 'CLR-001' in ids
    assert 'SPE-001' in ids
    assert 'ACC-001' in ids
    assert 'ARC-001' in ids
    assert not any(x.startswith('REQUIREMENTS-') for x in ids)
    assert not any(x.startswith('CLARIFICATION-') for x in ids)


def test_approval_materializes_dependency_relations_and_project_event_subject(tmp_path):
    import json
    from thesys_cli.main import main
    from thesys_engine.registry import get
    main(['init','--path',str(tmp_path)])
    main(['intent','create','Build a platform.','--path',str(tmp_path)])
    main(['discovery','propose','--agent','mock','--path',str(tmp_path)])
    main(['discovery','accept','--path',str(tmp_path)])
    main(['generate','governance','--agent','mock','--path',str(tmp_path)])
    main(['proposal','accept','governance','--path',str(tmp_path)])
    registry=get(tmp_path)
    ids=registry['artifacts']
    assert any(r['source']==ids['GOV-001']['id'] and r['target']==ids['INT-001']['id'] and r['relation']=='depends-on' for r in registry['relations'])
    from thesys_engine.project import project_info
    project_key=project_info(tmp_path)['key']
    assert any(e['kind']=='project-initialized' and e['subject']==project_key for e in registry['events'])
