from pathlib import Path
from thesys_engine.methodology import load_methodology
ROOT=Path(__file__).parents[1]

def test_lifecycle_is_well_formed():
    m=load_methodology(ROOT)
    ids=[s.id for s in m.stages]
    assert ids[0]=='intent'
    assert ids[-1]=='retirement'
    assert 'implementation' in ids
    assert m.rules['human_may_only_approve_existing_ai_proposal'] is True
    assert m.rules['implementation']['execute_generated_code'] is False

def test_delivery_release_is_inside_full_lifecycle():
    m=load_methodology(ROOT)
    release=m.stage('release')
    assert release.config.get('delivery_milestone') is True
    assert 'operation' in [s.id for s in m.stages]
    assert 'evolution' in [s.id for s in m.stages]
    assert 'retirement' in [s.id for s in m.stages]
