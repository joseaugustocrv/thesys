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
    assert [p.id for p in m.phases] == ['discovery-foundation','definition','design','engineering-assurance','delivery','verification','release-operation']
    assert m.stage('engineering-units').phase_id == 'discovery-foundation'
    assert m.stage('engineering-units').action == 'units'
    assert m.stage('engineering-units').config.get('scope') == 'project'
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


def test_methodology_declares_runtime_owned_question_identity():
    methodology = load_methodology(Path(__file__).parents[1])
    assert methodology.version == '0.6.0'
    assert methodology.rules['clarification_question_identity_is_runtime_owned'] is True
    assert methodology.rules['clarification_question_ids_are_project_wide_and_canonical'] is True
    assert methodology.rules['agents_must_not_assign_clarification_question_ids'] is True


def test_methodology_declares_model_owned_question_blocking_policy():
    m = load_methodology(ROOT)
    policy = m.rules['question_blocking']
    assert policy['model_decides'] is True
    assert policy['unresolved_blocking_questions_stop_progression'] is True
    assert 'current stage' in policy['blocking_definition']
    assert 'later' in policy['non_blocking_definition']
