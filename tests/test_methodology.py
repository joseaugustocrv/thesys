from pathlib import Path
from thesys_engine.methodology import load_methodology
ROOT=Path(__file__).parents[1]

def test_lifecycle_is_well_formed():
    m=load_methodology(ROOT)
    ids=[s.id for s in m.stages]
    assert ids[0]=='intent'
    assert ids[-1]=='retirement'
    assert 'implementation' in ids
    assert 'system-architecture' in ids
    assert m.stage('system-architecture').config.get('scope') == 'project'
    assert m.stage('system-architecture').config.get('aggregate_units') is True
    assert all(s.config.get('artifact_prefix') for s in m.stages)
    assert m.rules['human_may_only_approve_existing_ai_proposal'] is True
    assert m.rules['implementation']['execute_generated_code'] is False
    assert m.rules['engineering_units_control_complexity'] is True
    assert m.rules['system_architecture_synthesizes_unit_architectures'] is True

def test_delivery_release_is_inside_full_lifecycle():
    m=load_methodology(ROOT)
    release=m.stage('release')
    assert release.config.get('delivery_milestone') is True
    assert 'operation' in [s.id for s in m.stages]
    assert 'evolution' in [s.id for s in m.stages]
    assert 'retirement' in [s.id for s in m.stages]
