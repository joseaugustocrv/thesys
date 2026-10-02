from pathlib import Path
import json
from thesys_cli.main import main
from thesys_engine.methodology import load_methodology
from thesys_engine.gates import status
ROOT=Path(__file__).parents[1]

def test_question_loop_invalidates_and_regenerates(tmp_path):
    main(['init','--path',str(tmp_path)])
    main(['intent','create','Build a platform [[QUESTION:policy]]','--path',str(tmp_path)])
    assert main(['discovery','propose','--agent','mock','--path',str(tmp_path)])==0
    m=load_methodology(ROOT)
    assert status(tmp_path,m)['intent']['status']=='questions_pending'
    assert main(['question','answer','QST-001','Use secure authentication and protect financial data.','--path',str(tmp_path)])==0
    assert status(tmp_path,m)['intent']['status']=='needs_regeneration'
    assert main(['discovery','propose','--agent','mock','--path',str(tmp_path)])==0
    assert status(tmp_path,m)['intent']['status']=='proposed'
    assert main(['discovery','accept','--path',str(tmp_path)])==0


def test_discovery_prompt_stops_at_intent_boundary(tmp_path):
    from thesys_engine.agents import OpenAIAgent

    class FakeResponses:
        def create(self, **kwargs):
            self.kwargs = kwargs
            class Result:
                output_text = json.dumps({
                    "intent": "A sufficiently detailed proposed intent for the test project.",
                    "context": "A sufficiently detailed engineering context for the test project.",
                    "questions": [],
                })
            return Result()

    class FakeClient:
        def __init__(self):
            self.responses = FakeResponses()

    client = FakeClient()
    agent = OpenAIAgent(client=client)
    (tmp_path / ".thesys").mkdir()
    (tmp_path / ".thesys" / "project.yaml").write_text("key: test\n", encoding="utf-8")
    agent.propose_discovery(load_methodology(ROOT), "Build a finance platform", {}, tmp_path)
    instructions = client.responses.kwargs["instructions"]
    assert "Discovery defines intent, not detailed requirements" in instructions
    assert "If the remaining unknowns can be resolved downstream" in instructions


def test_discovery_accept_keeps_lifecycle_status_out_of_intent_content(tmp_path):
    from thesys_engine.intents import accept_discovery
    from thesys_engine.methodology import load_methodology
    from thesys_engine.workflow import save_proposal
    from thesys_engine.gates import status

    main(['init','--path',str(tmp_path)])
    project=tmp_path
    main(['intent','create','Build a platform','--path',str(tmp_path)])
    m=load_methodology(ROOT)
    intent = "# Intent — Plataforma\n\n## Propósito\n\nCriar uma solução para pequenas empresas.\n\n## Questões em aberto\n\nNenhuma.\n"
    context = "# Contexto — Plataforma\n\n## Contexto\n\nContexto válido."
    inputs={'intent_input':(project/'engineering/intent/input.md').read_text(encoding='utf-8-sig'),'answers':{},'project_template':(project/'.thesys/project.yaml').read_text(encoding='utf-8-sig')}
    save_proposal(project,'intent',project.name,'mock',json.dumps({'intent':intent,'context':context},ensure_ascii=False),[],inputs)
    accept_discovery(project,m)
    content=(project/'engineering/intent/intent.md').read_text(encoding='utf-8-sig')
    assert 'Status:' not in content
    assert 'Owner:' not in content
    assert 'Version:' not in content
    assert status(project,m)['intent']['status'] == 'approved'
    assert not (project/f'engineering/context/{tmp_path.name}/context.md').exists()


def test_write_text_is_windows_utf8_compatible(tmp_path):
    from thesys_engine.io import write_text, read_text
    p=tmp_path/'artifact.md'
    write_text(p,'# Intent — Plataforma\n\nAprovação e informação: ação.')
    assert not p.read_bytes().startswith(b'\xef\xbb\xbf')
    assert read_text(p) == '# Intent — Plataforma\n\nAprovação e informação: ação.'


def test_answered_questions_remain_in_documentation_history_after_regeneration(tmp_path):
    main(['init','--path',str(tmp_path)])
    main(['config','set','agent_provider','mock','--path',str(tmp_path)])
    main(['intent','create','Build a platform [[QUESTION:policy]]','--path',str(tmp_path)])
    assert main(['next','--path',str(tmp_path)]) == 0
    answer='A organização exige aprovação antes de alterações relevantes.'
    assert main(['question','answer','QST-001',answer,'--path',str(tmp_path)]) == 0
    assert main(['next','--path',str(tmp_path)]) == 0
    html=(tmp_path/'.thesys/docs/index.html').read_text(encoding='utf-8-sig')
    assert answer in html
    assert 'QST-001' in html


def test_runtime_does_not_semantically_resolve_answered_questions(tmp_path):
    """Runtime preserves model ownership of semantic resolution decisions."""
    from thesys_engine.workflow import save_proposal
    from thesys_engine.methodology import load_methodology
    m=load_methodology(ROOT)
    main(['init','--path',str(tmp_path)])
    main(['intent','create','Build a platform.','--path',str(tmp_path)])
    question={"question":"Qual é o estilo arquitetural?","why":"A decisão é necessária para aprovar a arquitetura.","blocking":True}
    save_proposal(tmp_path,'architecture','test-project','mock','Contexto inicial',[question],{'source':'first'},m)
    main(['question','answer','QST-001','SUA RESPOSTA','--path',str(tmp_path)])
    regenerated={"question":"Qual estilo arquitetural deve ser adotado?","why":"A decisão continua necessária para aprovar a arquitetura.","blocking":True}
    save_proposal(tmp_path,'architecture','test-project','mock','Contexto regenerado',[regenerated],{'source':'second'},m)
    proposal=json.loads((tmp_path / '.thesys' / 'proposals' / tmp_path.name / 'architecture.json').read_text(encoding='utf-8-sig'))
    assert proposal['questions'][0]['id']=='QST-002'
    assert proposal['questions'][0]['blocking'] is True
    assert proposal['clarification_history'][0]['id']=='QST-001'
    assert proposal['clarification_history'][0]['answer']=='SUA RESPOSTA'


def test_json_artifacts_are_windows_utf8_compatible(tmp_path):
    main(['init','--path',str(tmp_path)])
    p=tmp_path/'.thesys'/'project.yaml'
    # JSON is emitted as standards-compliant UTF-8 without a BOM.
    # generated state without mojibake.
    from thesys_engine.io import write_text
    j=tmp_path/'.thesys'/'sample.json'
    write_text(j,'{"texto":"Aprovação e integração"}\n')
    assert not j.read_bytes().startswith(b'\xef\xbb\xbf')
    assert json.loads(j.read_text(encoding='utf-8-sig'))['texto']=='Aprovação e integração'


def test_runtime_assigns_canonical_question_ids_and_ignores_model_identity(tmp_path):
    from thesys_engine.workflow import save_proposal

    main(['init', '--path', str(tmp_path)])
    main(['intent', 'create', 'Build a platform.', '--path', str(tmp_path)])
    methodology = load_methodology(ROOT)
    save_proposal(
        tmp_path,
        'intent',
        'test-project',
        'mock',
        'proposal',
        [{
            'id': 'Q1',
            'question': 'Quais usuários serão atendidos?',
            'why': 'A definição dos usuários orienta a intenção.',
            'blocking': True,
        }],
        {'source': 'first'},
        methodology,
    )
    proposal = json.loads((tmp_path / '.thesys' / 'proposals' / tmp_path.name / 'intent.json').read_text(encoding='utf-8'))
    assert proposal['questions'][0]['id'] == 'QST-001'


def test_runtime_preserves_question_identity_and_history_across_regeneration(tmp_path):
    from thesys_engine.workflow import save_proposal

    main(['init', '--path', str(tmp_path)])
    main(['intent', 'create', 'Build a platform.', '--path', str(tmp_path)])
    methodology = load_methodology(ROOT)
    save_proposal(
        tmp_path, 'intent', 'test-project', 'mock', 'first',
        [{'question': 'Quais usuários serão atendidos?', 'why': 'Define os usuários.', 'blocking': True}],
        {'source': 'first'}, methodology,
    )
    first_path = tmp_path / '.thesys' / 'proposals' / tmp_path.name / 'intent.json'
    first = json.loads(first_path.read_text(encoding='utf-8'))
    assert first['questions'][0]['id'] == 'QST-001'

    main(['question', 'answer', 'QST-001', 'Vendedores e gestores.', '--path', str(tmp_path)])
    save_proposal(
        tmp_path, 'intent', 'test-project', 'mock', 'second',
        [{'question': 'Quais são os principais usuários do sistema?', 'why': 'Define os usuários principais.', 'blocking': True}],
        {'source': 'second'}, methodology,
    )
    second = json.loads(first_path.read_text(encoding='utf-8'))
    assert second['questions'][0]['id'] == 'QST-002'
    assert second['questions'][0]['blocking'] is True
    assert second['clarification_history'][0]['id'] == 'QST-001'
    assert second['clarification_history'][0]['answer'] == 'Vendedores e gestores.'


def test_question_answer_requires_runtime_canonical_id(tmp_path):
    from thesys_engine.errors import ProjectError
    from thesys_engine.workflow import answer_question

    main(['init', '--path', str(tmp_path)])
    try:
        answer_question(tmp_path, 'Q1', 'Resposta')
    except ProjectError as exc:
        assert 'QST-NNN' in str(exc)
    else:
        raise AssertionError('Non-canonical question IDs must be rejected.')


def test_question_ids_are_project_wide_and_never_reused(tmp_path):
    from thesys_engine.workflow import save_proposal

    main(['init', '--path', str(tmp_path)])
    main(['intent', 'create', 'Build a platform.', '--path', str(tmp_path)])
    methodology = load_methodology(ROOT)
    question = {'question': 'Qual é o objetivo de negócio?', 'why': 'Define o resultado.', 'blocking': True}
    save_proposal(tmp_path, 'intent', tmp_path.name, 'mock', 'intent', [question], {'stage': 'intent'}, methodology)
    save_proposal(tmp_path, 'governance', tmp_path.name, 'mock', 'governance', [question], {'stage': 'governance'}, methodology)

    intent = json.loads((tmp_path / '.thesys' / 'proposals' / tmp_path.name / 'intent.json').read_text(encoding='utf-8'))
    governance = json.loads((tmp_path / '.thesys' / 'proposals' / tmp_path.name / 'governance.json').read_text(encoding='utf-8'))
    assert intent['questions'][0]['id'] == 'QST-001'
    assert governance['questions'][0]['id'] == 'QST-002'



def test_runtime_preserves_model_blocking_decision_for_clarification(tmp_path):
    from thesys_engine.workflow import save_proposal
    main(['init', '--path', str(tmp_path)])
    methodology = load_methodology(ROOT)
    questions = [
        {'question': 'Quais são os campos definitivos da operação?', 'why': 'A decisão é necessária antes de aprovar o baseline.', 'blocking': True},
        {'question': 'Quais são os campos definitivos da operação?', 'why': 'O detalhamento pertence à Specification.', 'blocking': False},
    ]
    save_proposal(tmp_path, 'clarification', tmp_path.name, 'mock', 'clarification', questions, {'source': 'test'}, methodology)
    proposal = json.loads((tmp_path / '.thesys' / 'proposals' / tmp_path.name / 'clarification.json').read_text(encoding='utf-8-sig'))
    assert [q['blocking'] for q in proposal['questions']] == [True, False]


def test_runtime_requires_boolean_blocking_value(tmp_path):
    from thesys_engine.errors import ProjectError
    from thesys_engine.workflow import save_proposal
    main(['init', '--path', str(tmp_path)])
    methodology = load_methodology(ROOT)
    try:
        save_proposal(
            tmp_path, 'clarification', 'test-project', 'mock', 'clarification',
            [{'question': 'Uma pergunta válida?', 'why': 'Motivo válido.', 'blocking': 'true'}],
            {'source': 'test'}, methodology,
        )
    except ProjectError as exc:
        assert "blocking' must be a boolean" in str(exc)
    else:
        raise AssertionError('Runtime must reject non-boolean blocking values.')
