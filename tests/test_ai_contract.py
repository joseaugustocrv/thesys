import json
from pathlib import Path
from thesys_engine.agents import OpenAIAgent
from thesys_engine.methodology import load_methodology
from thesys_cli.main import main

ROOT=Path(__file__).parents[1]

class FakeResponses:
    def __init__(self,payload): self.payload=payload; self.calls=[]
    def create(self,**kwargs):
        self.calls.append(kwargs)
        class R:
            output_text=''
        r=R(); r.output_text=__import__('json').dumps(self.payload); return r

class FakeClient:
    def __init__(self,payload): self.responses=FakeResponses(payload)

def test_openai_discovery_contract_is_structured(tmp_path):
    payload={'intent_sections': {k:'content' for k in __import__('thesys_engine.templates',fromlist=['template_contract']).template_contract(load_methodology(ROOT),'intent').section_ids}, 'context_sections': {k:'content' for k in __import__('thesys_engine.templates',fromlist=['template_contract']).template_contract(load_methodology(ROOT),'context').section_ids}, 'questions':[]}
    client=FakeClient(payload); agent=OpenAIAgent(client); m=load_methodology(ROOT)
    (tmp_path/'.thesys').mkdir(); (tmp_path/'.thesys/project.yaml').write_text('key: test\nname: Test\ntemplate: software-system\n',encoding='utf8')
    result=agent.propose_discovery(m,'Build a system.',{},tmp_path)
    assert result['questions']==[]
    call=client.responses.calls[0]
    assert call['model']=='gpt-5.6-luna'
    assert call['text']['format']['type']=='json_schema'
    assert 'Project language: en-US' in call['instructions']
    assert 'template defines the document structure' in call['instructions']

def test_openai_stage_contract_returns_questions():
    m=load_methodology(ROOT)
    payload={'sections': {k:'Proposed content. ' * 20 for k in __import__('thesys_engine.templates',fromlist=['template_contract']).template_contract(m,'requirements').section_ids},'questions':[{'question':'What is the retention target?','why':'It affects architecture.','blocking':True}]}
    client=FakeClient(payload); agent=OpenAIAgent(client); m=load_methodology(ROOT)
    from thesys_engine.agents import GenerationContext
    result=agent.propose_document(m,'requirements',GenerationContext('intent','default','scope','pt-BR',{},{}))
    assert result['questions'][0]['blocking'] is True
    call=client.responses.calls[0]
    assert 'Project language: pt-BR' in call['instructions']
    assert 'template defines the document structure' in call['instructions']


def test_openai_unit_contract_canonicalizes_localized_type():
    from thesys_engine.unit_proposals import OpenAIUnitAgent

    payload={
        "decompose": True,
        "engineering_units": [{
            "key": "sales",
            "name": "Vendas",
            "scope": "Operações de vendas",
            "rationale": "Domínio explicitamente definido no Intent.",
            "type": "domínio",
            "parent": "default",
            "dependencies": [],
        }],
    }
    client=FakeClient(payload)
    result=OpenAIUnitAgent(client).propose_units("# Intent\n\nERP")
    assert result.decompose is True
    assert result.units[0].unit_type == "domain"
    call=client.responses.calls[0]
    unit_type=call["text"]["format"]["schema"]["properties"]["engineering_units"]["items"]["properties"]["type"]
    assert unit_type["enum"]
    assert "domain" in unit_type["enum"]
    assert "domínio" not in unit_type["enum"]


def test_agent_question_contract_delegates_identity_to_runtime():
    from thesys_engine.agents import _question_schema

    schema = _question_schema()
    assert set(schema["properties"]) == {"question", "why", "blocking"}
    assert "id" not in schema["required"]
    assert schema["properties"]["blocking"]["type"] == "boolean"
    assert schema["additionalProperties"] is False


def test_openai_discovery_schema_does_not_allow_model_assigned_question_ids():
    m = load_methodology(ROOT)
    payload = {
        "intent_sections": {key: "content" for key in __import__(
            "thesys_engine.templates", fromlist=["template_contract"]
        ).template_contract(m, "intent").section_ids},
        "context_sections": {key: "content" for key in __import__(
            "thesys_engine.templates", fromlist=["template_contract"]
        ).template_contract(m, "context").section_ids},
        "questions": [],
    }
    client = FakeClient(payload)
    agent = OpenAIAgent(client)
    project = ROOT / "tests" / "_schema_project_tmp"
    project.mkdir(exist_ok=True)
    try:
        (project / ".thesys").mkdir(exist_ok=True)
        (project / ".thesys" / "project.yaml").write_text(
            "key: test\nname: Test\ntemplate: software-system\n", encoding="utf-8"
        )
        agent.propose_discovery(m, "Build a system.", {}, project)
        question_items = client.responses.calls[0]["text"]["format"]["schema"]["properties"]["questions"]["items"]
        assert "id" not in question_items["properties"]
        assert "id" not in question_items["required"]
    finally:
        import shutil
        shutil.rmtree(project, ignore_errors=True)



def test_stage_prompt_exposes_complete_lifecycle_for_question_classification():
    m = load_methodology(ROOT)
    payload = {
        'sections': {k: 'content' for k in __import__('thesys_engine.templates', fromlist=['template_contract']).template_contract(m, 'clarification').section_ids},
        'questions': [],
    }
    client = FakeClient(payload)
    agent = OpenAIAgent(client)
    from thesys_engine.agents import GenerationContext
    agent.propose_document(m, 'clarification', GenerationContext('intent', 'default', 'scope', 'pt-BR', {}, {}))
    call = client.responses.calls[0]
    instructions = call['instructions']
    assert 'apply the question-blocking policy defined by the methodology' in instructions
    lifecycle_input = call['input']
    assert 'Complete lifecycle contract:' in lifecycle_input
    assert 'specification' in lifecycle_input
    assert 'implementation' in lifecycle_input
    assert 'depends_on' in lifecycle_input
    assert 'runtime does not reinterpret it by topic, keyword, or stage-specific heuristic' in instructions
    assert 'Human answers are evidence that must be evaluated, not proof that the corresponding decision was resolved.' in instructions
    assert 'the unresolved issue MUST be returned as a new entry in the questions array with blocking=true' in instructions
    assert 'Do not assign or reuse question IDs; the Thesys runtime assigns question IDs after generation.' in instructions
    assert 'Questions are proposal metadata, never artifact content.' in instructions


def test_model_blocking_decision_is_preserved_without_semantic_runtime_override(tmp_path):
    from thesys_engine.workflow import save_proposal
    main(['init', '--path', str(tmp_path)])
    m = load_methodology(ROOT)
    questions = [
        {'question': 'Quais são os campos definitivos da operação?', 'why': 'A decisão ainda pode ser necessária nesta fase.', 'blocking': True},
        {'question': 'Quais são os campos definitivos da operação?', 'why': 'O detalhamento pode ser resolvido na Specification.', 'blocking': False},
    ]
    save_proposal(tmp_path, 'clarification', 'default', 'mock', 'clarification', questions, {'source': 'test'}, m)
    proposal = __import__('json').loads((tmp_path / '.thesys/proposals/default/clarification.json').read_text(encoding='utf-8-sig'))
    assert [q['blocking'] for q in proposal['questions']] == [True, False]


def test_stage_prompt_receives_clarification_history(tmp_path):
    from thesys_engine.agents import OpenAIAgent, GenerationContext
    from thesys_engine.methodology import load_methodology
    m=load_methodology(ROOT)

    class FakeResponses:
        def create(self, **kwargs):
            self.kwargs=kwargs
            class Result:
                output_text=json.dumps({"sections": {k:"content" for k in __import__("thesys_engine.templates",fromlist=["template_contract"]).template_contract(m,"architecture").section_ids}, "questions":[]})
            return Result()
    class FakeClient:
        def __init__(self): self.responses=FakeResponses()

    agent=OpenAIAgent(client=FakeClient())
    history=[{"id":"QST-021","question":"Qual estilo arquitetural?","why":"Necessário para aprovação.","blocking":True,"answer":"SUA RESPOSTA","stage":"architecture","unit":"default"}]
    agent.propose_document(m,"architecture",GenerationContext("intent","default","scope","pt-BR",{}, {}, {}, "system", None, (), history))
    assert "Clarification history for this stage and unit" in agent.client.responses.kwargs["input"]
    assert "QST-021" in agent.client.responses.kwargs["input"]
