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


def test_discovery_accept_marks_localized_intent_authoritative(tmp_path):
    from thesys_engine.intents import accept_discovery
    from thesys_engine.methodology import load_methodology
    from thesys_engine.workflow import save_proposal

    main(['init','--path',str(tmp_path)])
    project=tmp_path
    main(['intent','create','Build a platform','--path',str(tmp_path)])
    m=load_methodology(ROOT)
    intent = "# Intent — Plataforma\n\n**Status da proposta:** Não autoritativa; requer aprovação humana.\n\n## Propósito\n\nCriar uma solução para pequenas empresas.\n\n## Intent status\n\n**Status:** Proposta consolidada — aguardando aprovação humana"
    context = "# Contexto — Plataforma\n\n## Contexto\n\nContexto válido.\n\nStatus: Proposta não autoritativa; aguardando aprovação humana."
    inputs={'intent_input':(project/'engineering/intent/input.md').read_text(encoding='utf-8-sig'),'answers':{},'project_template':(project/'.thesys/project.yaml').read_text(encoding='utf-8')}
    save_proposal(project,'intent','default','mock',json.dumps({'intent':intent,'context':context},ensure_ascii=False),[],inputs)
    accept_discovery(project,m)
    content=(project/'engineering/intent/intent.md').read_text(encoding='utf-8-sig')
    assert 'Não autoritativa' not in content
    assert 'aguardando aprovação humana' not in content
    assert '**Status da proposta:** Autoritativa.' in content
    assert '**Status:** Authoritative' in content


def test_write_text_is_windows_utf8_compatible(tmp_path):
    from thesys_engine.io import write_text, read_text
    p=tmp_path/'artifact.md'
    write_text(p,'# Intent — Plataforma\n\nAprovação e informação: ação.')
    assert p.read_bytes().startswith(b'\xef\xbb\xbf')
    assert read_text(p) == '# Intent — Plataforma\n\nAprovação e informação: ação.'
