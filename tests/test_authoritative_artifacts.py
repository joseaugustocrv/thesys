import hashlib
import json
from pathlib import Path

from thesys_cli.main import main
from thesys_engine.registry import get

ROOT = Path(__file__).parents[1]


def test_proposal_accept_preserves_document_content_and_registry_is_authoritative(tmp_path):
    def cli(*args):
        return main(list(args) + ['--path', str(tmp_path)])

    assert cli('init') == 0
    assert cli('intent', 'create', 'Build a system.') == 0
    assert cli('discovery', 'propose', '--agent', 'mock') == 0
    assert cli('discovery', 'accept') == 0
    assert cli('generate', 'governance', '--agent', 'mock') == 0

    proposal_path = tmp_path / '.thesys' / 'proposals' / 'default' / 'governance.json'
    proposal = json.loads(proposal_path.read_text(encoding='utf-8-sig'))
    original_content = proposal['content']
    proposal_path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    assert cli('proposal', 'accept', 'governance') == 0

    artifact = tmp_path / 'engineering' / 'governance' / 'governance.md'
    content = artifact.read_text(encoding='utf-8-sig')
    assert content == original_content.rstrip() + '\n'

    registry = get(tmp_path)
    governance = next(v for v in registry['artifacts'].values() if v['type'] == 'GOV')
    assert governance['status'] == 'authoritative'
    assert governance['authority'] == 'human'

    approvals = json.loads((tmp_path / '.thesys' / 'approvals.json').read_text(encoding='utf-8-sig'))
    approval = approvals['approvals']['governance:default']
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert approval['sha256'] == digest


def test_lifecycle_metadata_is_not_rendered_inside_artifacts(tmp_path):
    from thesys_engine.methodology import load_methodology
    from thesys_engine.templates import render_template, template_contract

    m = load_methodology(ROOT)
    lifecycle_metadata_markers = (
        '**Status:** Draft',
        '**Status:** Rascunho',
        'Status: Draft',
        'Status: Rascunho',
        '**Status da proposta:**',
        '**Status da intenção:**',
        '**Version:** 0.1',
        '**Versão:** 0.1',
        '**Owner:** [Owner]',
        '**Responsável:** [Owner]',
    )
    for stage_id in (
        'intent', 'governance', 'context', 'requirements', 'specification',
        'architecture', 'system-architecture', 'quality', 'security', 'risk',
        'plan', 'acceptance', 'verification', 'operation', 'evolution',
        'retirement',
    ):
        sections = {section.id: '' for section in template_contract(m, stage_id).sections}
        content = render_template(m, stage_id, sections, 'pt-BR', 'default')
        assert not any(marker in content for marker in lifecycle_metadata_markers), stage_id
