import json
from pathlib import Path
import pytest

from thesys_cli.main import main
from thesys_engine.errors import ProjectError
from thesys_engine.gates import status
from thesys_engine.methodology import load_methodology
from thesys_engine.registry import get

ROOT = Path(__file__).parents[1]


def cli(project, *args):
    return main([*args, '--path', str(project)])


def prepare_units(project):
    assert cli(project, 'init') == 0
    assert cli(project, 'intent', 'create', 'Build an ERP with finance, inventory and sales domains.') == 0
    assert cli(project, 'discovery', 'propose', '--agent', 'mock') == 0
    assert cli(project, 'discovery', 'accept') == 0
    assert cli(project, 'generate', 'governance', '--agent', 'mock') == 0
    assert cli(project, 'proposal', 'accept', 'governance') == 0
    assert cli(project, 'unit', 'create', 'finance', 'Finance', '--type', 'domain', '--scope', 'Financial operations') == 0
    assert cli(project, 'unit', 'create', 'inventory', 'Inventory', '--type', 'domain', '--scope', 'Inventory operations') == 0


def approve_unit_through_architecture(project, unit):
    for stage in ['context', 'requirements', 'clarification', 'specification', 'acceptance', 'architecture']:
        assert cli(project, 'generate', stage, '--unit', unit, '--agent', 'mock') == 0
        assert cli(project, 'proposal', 'accept', stage, '--unit', unit) == 0


def test_large_project_uses_unit_artifacts_and_integrates_architecture(tmp_path):
    prepare_units(tmp_path)
    approve_unit_through_architecture(tmp_path, 'finance')
    approve_unit_through_architecture(tmp_path, 'inventory')

    m = load_methodology(ROOT)
    assert status(tmp_path, m, 'finance')['architecture']['status'] == 'approved'
    assert status(tmp_path, m, 'inventory')['architecture']['status'] == 'approved'
    assert status(tmp_path, m, 'default')['requirements']['status'] == 'not_applicable'

    assert cli(tmp_path, 'generate', 'system-architecture', '--agent', 'mock') == 0
    proposal = json.loads((tmp_path / '.thesys/proposals/default/system-architecture.json').read_text(encoding='utf-8'))
    assert 'architecture:finance' in proposal['content'] or 'finance' in proposal['content']
    assert cli(tmp_path, 'proposal', 'accept', 'system-architecture') == 0

    artifact = tmp_path / 'engineering/architecture/system-architecture.md'
    assert artifact.is_file()
    content = artifact.read_text(encoding='utf-8')
    assert 'Finance (finance)' in content
    assert 'Inventory (inventory)' in content
    assert '[UNIT]' not in content
    assert status(tmp_path, m, 'finance')['system-architecture']['status'] == 'approved'

    registry = get(tmp_path)
    system_arc = next(k for k,v in registry['artifacts'].items() if v['path'].endswith('system-architecture.md'))
    unit_arcs = [k for k,v in registry['artifacts'].items() if v['type'] == 'ARC' and v['unit'] in {'finance','inventory'}]
    assert len(unit_arcs) == 2
    assert all(any(e['source'] == system_arc and e['target'] == unit_arc and e['relation'] == 'synthesizes' for e in registry['relations']) for unit_arc in unit_arcs)

    for unit in ['finance', 'inventory']:
        for stage in ['quality', 'security', 'risk', 'plan', 'tasks']:
            assert cli(tmp_path, 'generate', stage, '--unit', unit, '--agent', 'mock') == 0
            assert cli(tmp_path, 'proposal', 'accept', stage, '--unit', unit) == 0
        assert status(tmp_path, m, unit)['tasks']['status'] == 'approved'


def test_system_architecture_requires_all_unit_architectures(tmp_path):
    prepare_units(tmp_path)
    approve_unit_through_architecture(tmp_path, 'finance')
    with pytest.raises(ProjectError):
        cli(tmp_path, 'generate', 'system-architecture', '--agent', 'mock')


def test_unit_scope_is_required_after_decomposition(tmp_path):
    prepare_units(tmp_path)
    with pytest.raises(ProjectError):
        cli(tmp_path, 'generate', 'requirements', '--agent', 'mock')


def test_unit_architecture_change_invalidates_system_architecture(tmp_path):
    prepare_units(tmp_path)
    approve_unit_through_architecture(tmp_path, 'finance')
    approve_unit_through_architecture(tmp_path, 'inventory')
    assert cli(tmp_path, 'generate', 'system-architecture', '--agent', 'mock') == 0
    assert cli(tmp_path, 'proposal', 'accept', 'system-architecture') == 0

    architecture = tmp_path / 'engineering/architecture/finance/architecture.md'
    architecture.write_text(architecture.read_text(encoding='utf-8') + '\n## Changed boundary\n', encoding='utf-8')
    m = load_methodology(ROOT)
    assert status(tmp_path, m, 'finance')['architecture']['status'] == 'needs_revalidation'
    assert status(tmp_path, m, 'finance')['system-architecture']['status'] == 'needs_revalidation'
