import hashlib
import json
from pathlib import Path

from thesys_cli.main import main
from thesys_engine.registry import get

ROOT = Path(__file__).parents[1]


def test_proposal_accept_materializes_authoritative_status_and_preserves_content(tmp_path):
    def cli(*args):
        return main(list(args) + ['--path', str(tmp_path)])

    assert cli('init') == 0
    assert cli('intent', 'create', 'Build a system.') == 0
    assert cli('discovery', 'propose', '--agent', 'mock') == 0
    assert cli('discovery', 'accept') == 0
    assert cli('generate', 'governance', '--agent', 'mock') == 0

    proposal_path = tmp_path / '.thesys' / 'proposals' / 'default' / 'governance.json'
    proposal = json.loads(proposal_path.read_text(encoding='utf-8'))
    proposal['content'] = proposal['content'].replace('Status: Draft', 'Status: Draft')
    original_content = proposal['content']
    proposal_path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    assert cli('proposal', 'accept', 'governance') == 0

    artifact = tmp_path / 'engineering' / 'governance' / 'governance.md'
    content = artifact.read_text(encoding='utf-8')
    assert 'Status: Authoritative' in content
    assert 'Status: Draft' not in content
    expected = original_content.replace('Status: Draft', 'Status: Authoritative').rstrip() + '\n'
    assert content.lstrip('\ufeff') == expected

    registry = get(tmp_path)
    governance = next(v for v in registry['artifacts'].values() if v['type'] == 'GOV')
    assert governance['status'] == 'authoritative'
    assert governance['authority'] == 'human'

    approvals = json.loads((tmp_path / '.thesys' / 'approvals.json').read_text(encoding='utf-8'))
    approval = approvals['approvals']['governance:default']
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert approval['sha256'] == digest


def test_authoritative_materialization_only_changes_explicit_status_metadata():
    from thesys_engine.workflow import _materialize_authoritative_content

    content = '''# Example\n\nStatus: Draft\n\nA sentence mentioning Draft must remain Draft.\n\n**Status:** Proposed\n\nStatus: Pass\n'''
    expected = '''# Example\n\nStatus: Authoritative\n\nA sentence mentioning Draft must remain Draft.\n\n**Status:** Authoritative\n\nStatus: Pass\n'''
    assert _materialize_authoritative_content(content) == expected
