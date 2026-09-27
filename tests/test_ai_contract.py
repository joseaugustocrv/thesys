from pathlib import Path
from thesys_engine.agents import OpenAIAgent
from thesys_engine.methodology import load_methodology

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
    payload={'intent':'# Intent\n\nA sufficiently detailed proposed intent. '*8,'context':'# Context\n\nA sufficiently detailed proposed context. '*8,'questions':[]}
    client=FakeClient(payload); agent=OpenAIAgent(client); m=load_methodology(ROOT)
    (tmp_path/'.thesys').mkdir(); (tmp_path/'.thesys/project.yaml').write_text('key: test\nname: Test\ntemplate: software-system\n',encoding='utf8')
    result=agent.propose_discovery(m,'Build a system.',{},tmp_path)
    assert result['questions']==[]
    call=client.responses.calls[0]
    assert call['model']=='gpt-5.6-luna'
    assert call['text']['format']['type']=='json_schema'

def test_openai_stage_contract_returns_questions():
    payload={'content':'# Requirements\n\nProposed content. '*80,'questions':[{'id':'QST-001','question':'What is the retention target?','why':'It affects architecture.','blocking':True}]}
    client=FakeClient(payload); agent=OpenAIAgent(client); m=load_methodology(ROOT)
    from thesys_engine.agents import GenerationContext
    result=agent.propose_document(m,'requirements',GenerationContext('intent','default','scope','en-US',{},{}))
    assert result['questions'][0]['blocking'] is True
