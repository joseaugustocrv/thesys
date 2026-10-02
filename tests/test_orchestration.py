import json
from pathlib import Path

from thesys_cli.main import main
from thesys_engine.orchestration import next_action
from thesys_engine.unit_proposals import UnitProposal, write_proposal
from thesys_engine.methodology import load_methodology


ROOT = Path(__file__).parents[1]


def cli(project, *args):
    return main([*args, "--path", str(project)])


def test_next_automatically_proposes_discovery_then_units_then_lifecycle(tmp_path):
    assert cli(tmp_path, "init") == 0

    # Before human Intent input exists, automation stops at the human-owned input.
    action = next_action(tmp_path, load_methodology(ROOT))
    assert action.kind == "human_input"

    assert cli(tmp_path, "config", "set", "agent_provider", "mock") == 0
    assert cli(tmp_path, "intent", "create",
               "Build an ERP for a building materials distributor.",
               "--outcome",
               "Integrate sales, purchasing, inventory and finance.") == 0
    intent_input = tmp_path / "engineering" / "intent" / "input.md"
    intent_input.write_text(
        intent_input.read_text(encoding='utf-8-sig')
        + "\n## Capabilities\n\n- Sales\n- Inventory\n",
        encoding="utf-8",
    )

    # `next` now performs discovery proposal generation; no explicit `discovery propose`.
    assert cli(tmp_path, "next") == 0
    discovery = tmp_path / ".thesys" / "proposals" / "test-project" / "intent.json"
    assert discovery.is_file()
    assert (tmp_path / ".thesys" / "docs" / "index.html").is_file()

    assert cli(tmp_path, "discovery", "accept") == 0

    # Discovery establishes only the Intent. Governance is the next project-level phase;
    # Context is generated only after Engineering Units are known.
    assert cli(tmp_path, "next") == 0
    assert (tmp_path / ".thesys" / "proposals" / "test-project" / "governance.json").is_file()
    assert cli(tmp_path, "proposal", "accept", "governance") == 0

    # Once those baselines are current, `next` automatically asks the configured
    # agent for Engineering Units. The proposal remains non-authoritative.
    assert cli(tmp_path, "next") == 0
    units_proposal = tmp_path / ".thesys" / "proposals" / "test-project" / "engineering-units.json"
    assert units_proposal.is_file()
    docs_after_units = (tmp_path / ".thesys" / "docs" / "index.html").read_text(encoding='utf-8-sig')
    assert "Engineering Unit" in docs_after_units or "Lifecycle" in docs_after_units
    payload = json.loads(units_proposal.read_text(encoding='utf-8-sig'))
    assert payload["status"] == "proposed"

    # Human acceptance remains explicit; it is not hidden by orchestration.
    assert cli(tmp_path, "unit", "proposal", "accept") == 0
    units = sorted(p.stem for p in (tmp_path / ".thesys" / "units").glob("*.json"))
    assert units == ["test-project", "finance-inventory-sales-purchasing"] or len(units) >= 2

    # Context is now proposed as a phase for every effective Engineering Unit.
    assert cli(tmp_path, "next") == 0
    proposal_files = list((tmp_path / ".thesys" / "proposals").rglob("context.json"))
    assert len(proposal_files) >= 1


def test_next_regenerates_stale_discovery_proposal_after_answers(tmp_path):
    assert cli(tmp_path, "init") == 0
    assert cli(tmp_path, "config", "set", "agent_provider", "mock") == 0
    intent = "Build an ERP for a distributor. [[QUESTION:business-constraint]]"
    assert cli(tmp_path, "intent", "create", intent) == 0

    # First next creates the AI discovery proposal with a blocking question.
    assert cli(tmp_path, "next") == 0
    proposal_path = tmp_path / ".thesys" / "proposals" / "test-project" / "intent.json"
    first = json.loads(proposal_path.read_text(encoding='utf-8-sig'))
    assert first["status"] == "proposed"
    assert first["questions"]

    # Answering the question makes the existing proposal stale. The next call
    # must regenerate it automatically instead of merely reporting that fact.
    assert cli(tmp_path, "question", "answer", "QST-001", "The distributor requires approval before inventory changes.") == 0
    before_id = first["proposal_id"]
    assert cli(tmp_path, "next") == 0

    second = json.loads(proposal_path.read_text(encoding='utf-8-sig'))
    assert second["status"] == "proposed"
    assert second["proposal_id"] != before_id
    assert second["input_fingerprint"] != first["input_fingerprint"]
    assert "business-constraint" in second["content"]


def test_next_never_auto_approves_a_current_proposal(tmp_path):
    assert cli(tmp_path, "init") == 0
    assert cli(tmp_path, "intent", "create", "Build a small software system.") == 0
    # Explicitly generate discovery to keep this test focused on the review gate.
    assert cli(tmp_path, "discovery", "propose", "--agent", "mock") == 0
    action = next_action(tmp_path, load_methodology(ROOT))
    assert action.kind in {"human_review", "answer_questions"}


def test_next_walks_multiple_units_and_system_architecture(tmp_path):
    assert cli(tmp_path, "init") == 0
    assert cli(tmp_path, "config", "set", "agent_provider", "mock") == 0
    assert cli(tmp_path, "intent", "create", "Build an ERP for a distributor.") == 0
    assert cli(tmp_path, "next") == 0
    assert cli(tmp_path, "discovery", "accept") == 0
    assert cli(tmp_path, "next") == 0
    assert cli(tmp_path, "proposal", "accept", "governance") == 0

    write_proposal(
        tmp_path,
        "mock",
        [
            UnitProposal("sales", "Sales", "Sales operations", "Explicit business domain.", "domain"),
            UnitProposal("inventory", "Inventory", "Inventory operations", "Explicit business domain.", "domain"),
        ],
    )
    assert cli(tmp_path, "unit", "proposal", "accept") == 0

    m = load_methodology(ROOT)
    for _ in range(100):
        action = next_action(tmp_path, m)
        if action.stage == "system-architecture" and action.kind == "human_review_stage":
            for unit in ["test-project"]:
                proposal = tmp_path / ".thesys" / "proposals" / unit / "system-architecture.json"
                if proposal.is_file():
                    assert cli(tmp_path, "proposal", "accept", "system-architecture", "--unit", unit) == 0
            break
        if action.kind in {"propose_stage", "regenerate_stage"}:
            assert cli(tmp_path, "next") == 0
        elif action.kind == "human_review_stage":
            units = [p.stem for p in (tmp_path / ".thesys" / "units").glob("*.json")]
            stage = action.stage
            for unit in units:
                proposal = tmp_path / ".thesys" / "proposals" / unit / f"{stage}.json"
                if proposal.is_file():
                    assert cli(tmp_path, "proposal", "accept", stage, "--unit", unit) == 0
        elif action.kind == "human_review":
            assert action.stage != "implementation"
            assert cli(tmp_path, "proposal", "accept", action.stage, "--unit", action.unit) == 0
            if action.stage == "system-architecture":
                break
        elif action.kind in {"propose", "propose_implementation", "verify"}:
            assert cli(tmp_path, "next") == 0
        else:
            raise AssertionError(action)
    else:
        raise AssertionError("System architecture was not reached")

    system_arch = tmp_path / "engineering" / "architecture" / "system-architecture.md"
    assert system_arch.is_file()
    content = system_arch.read_text(encoding='utf-8-sig')
    assert "Sales (sales)" in content
    assert "Inventory (inventory)" in content
    assert (tmp_path / ".thesys" / "docs" / "index.html").is_file()


def test_small_project_can_remain_on_default_unit(tmp_path):
    assert cli(tmp_path, "init") == 0
    assert cli(tmp_path, "config", "set", "agent_provider", "mock") == 0
    assert cli(tmp_path, "intent", "create", "Build a small internal tool.") == 0
    assert cli(tmp_path, "next") == 0
    assert cli(tmp_path, "discovery", "accept") == 0
    assert cli(tmp_path, "next") == 0
    assert cli(tmp_path, "proposal", "accept", "governance") == 0
    assert cli(tmp_path, "next") == 0
    assert cli(tmp_path, "unit", "proposal", "accept") == 0
    units = [p.stem for p in (tmp_path / ".thesys" / "units").glob("*.json")]
    assert units == []
    assert next_action(tmp_path, load_methodology(ROOT)).kind == "propose_stage"


def test_generic_proposal_accept_dispatches_discovery_contract(tmp_path):
    assert cli(tmp_path, "init") == 0
    assert cli(tmp_path, "config", "set", "agent_provider", "mock") == 0
    assert cli(tmp_path, "intent", "create", "Build a small internal tool.") == 0
    assert cli(tmp_path, "next") == 0
    # The generic proposal command must use the discovery acceptance contract
    # for the Intent stage, including its composite Intent+Context fingerprint.
    assert cli(tmp_path, "proposal", "accept", "intent") == 0
    assert (tmp_path / "engineering/intent/intent.md").is_file()
    assert not (tmp_path / "engineering/context/test-project/context.md").exists()



def test_engineering_units_proposal_show_and_accept_are_supported(tmp_path):
    from thesys_engine.methodology import load_methodology
    from thesys_engine.unit_proposals import write_proposal, UnitProposal

    main(['init','--path',str(tmp_path)])
    main(['intent','create','Build a distributed sales platform.','--path',str(tmp_path)])
    main(['discovery','propose','--agent','mock','--path',str(tmp_path)])
    main(['discovery','accept','--path',str(tmp_path)])
    main(['generate','governance','--agent','mock','--path',str(tmp_path)])
    main(['proposal','accept','governance','--path',str(tmp_path)])
    m=load_methodology(Path(__file__).parents[1])
    write_proposal(tmp_path,'mock',[UnitProposal('sales','Sales','Sales domain','Explicit domain','domain','test-project',())],True)
    assert main(['proposal','show','engineering-units','--path',str(tmp_path)]) == 0
    assert main(['proposal','accept','engineering-units','--path',str(tmp_path)]) == 0
    units=list((tmp_path/'.thesys/units').glob('*.json'))
    assert (tmp_path/'.thesys/units/sales.json').is_file()
    unit_data=json.loads((tmp_path/'.thesys/units' / 'sales.json').read_text(encoding='utf-8'))
    assert unit_data['parent'] == tmp_path.name


def test_next_reaches_and_accepts_plan_after_full_preimplementation_flow(tmp_path):
    assert cli(tmp_path, 'init') == 0
    assert cli(tmp_path, 'config', 'set', 'agent_provider', 'mock') == 0
    assert cli(tmp_path, 'config', 'set', 'language', 'pt-BR') == 0
    assert cli(
        tmp_path,
        'intent',
        'create',
        'ERP para uma distribuidora de materiais de construção, integrando vendas, compras, estoque e financeiro.',
        '--outcome',
        'Operação integrada entre vendas, compras, estoque e financeiro.',
        '--owner',
        'Equipe do projeto',
    ) == 0

    methodology = load_methodology(ROOT)
    for _ in range(100):
        action = next_action(tmp_path, methodology)
        if action.stage == 'plan' and action.kind == 'human_review_stage':
            proposal_files = sorted((tmp_path / '.thesys' / 'proposals').rglob('plan.json'))
            assert proposal_files
            for proposal_path in proposal_files:
                proposal = json.loads(proposal_path.read_text(encoding='utf-8-sig'))
                if proposal.get('status') == 'proposed':
                    assert cli(tmp_path, 'proposal', 'accept', 'plan', '--unit', proposal['unit']) == 0
            break

        if action.kind in {'answer_questions', 'answer_stage_questions'}:
            paths = [action.proposal] if action.kind == 'answer_questions' else sorted(
                (tmp_path / '.thesys' / 'proposals').rglob(f'{action.stage}.json')
            )
            for proposal_path in paths:
                proposal = json.loads(proposal_path.read_text(encoding='utf-8-sig'))
                for question in proposal.get('questions', []):
                    if question.get('blocking'):
                        assert cli(
                            tmp_path,
                            'question',
                            'answer',
                            question['id'],
                            'Decisão humana registrada para validação do fluxo.',
                        ) == 0
            continue

        if action.kind in {
            'propose_discovery', 'propose', 'propose_stage',
            'regenerate', 'regenerate_stage', 'propose_stage', 'propose_implementation', 'verify',
        }:
            assert cli(tmp_path, 'next') == 0
            continue

        if action.kind == 'human_review_stage':
            proposal_files = sorted((tmp_path / '.thesys' / 'proposals').rglob(f'{action.stage}.json'))
            for proposal_path in proposal_files:
                proposal = json.loads(proposal_path.read_text(encoding='utf-8-sig'))
                if proposal.get('status') == 'proposed':
                    assert cli(tmp_path, 'proposal', 'accept', action.stage, '--unit', proposal['unit']) == 0
            continue

        if action.kind == 'human_review':
            assert (cli(tmp_path, 'implementation', 'accept') if action.stage == 'implementation' else cli(tmp_path, 'proposal', 'accept', action.stage, '--unit', action.unit)) == 0
            continue

        raise AssertionError(f'Unexpected orchestration action: {action}')
    else:
        raise AssertionError('The lifecycle did not reach an approvable Plan within 100 transitions.')

    plan = tmp_path / 'engineering' / 'plan' / 'test-project' / 'plan.md'
    assert plan.is_file()


def test_regenerate_phase_only_rebuilds_stale_unit_proposal(tmp_path):
    assert cli(tmp_path, "init") == 0
    assert cli(tmp_path, "config", "set", "agent_provider", "mock") == 0
    assert cli(tmp_path, "intent", "create", "Build an ERP for a distributor.") == 0
    assert cli(tmp_path, "next") == 0
    assert cli(tmp_path, "discovery", "accept") == 0
    assert cli(tmp_path, "next") == 0
    assert cli(tmp_path, "proposal", "accept", "governance") == 0

    write_proposal(
        tmp_path,
        "mock",
        [
            UnitProposal("sales", "Sales", "Sales operations", "Explicit business domain.", "domain"),
            UnitProposal("purchasing", "Purchasing", "Purchasing operations", "Explicit business domain.", "domain"),
        ],
    )
    assert cli(tmp_path, "unit", "proposal", "accept") == 0
    assert cli(tmp_path, "next") == 0

    proposals = {}
    for unit in ("sales", "purchasing"):
        path = tmp_path / ".thesys" / "proposals" / unit / "context.json"
        proposals[unit] = json.loads(path.read_text(encoding="utf-8-sig"))

    # Simulate one answered question making only Sales stale. The phase action
    # must regenerate Sales without touching the current Purchasing proposal.
    sales_path = tmp_path / ".thesys" / "proposals" / "sales" / "context.json"
    sales = proposals["sales"]
    sales["status"] = "needs_regeneration"
    sales_path.write_text(json.dumps(sales, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    assert cli(tmp_path, "next") == 0
    sales_after = json.loads(sales_path.read_text(encoding="utf-8-sig"))
    purchasing_after = json.loads(
        (tmp_path / ".thesys" / "proposals" / "purchasing" / "context.json").read_text(encoding="utf-8-sig")
    )
    assert sales_after["proposal_id"] != proposals["sales"]["proposal_id"]
    assert purchasing_after["proposal_id"] == proposals["purchasing"]["proposal_id"]
    assert purchasing_after["questions"] == proposals["purchasing"]["questions"]


def test_question_gate_obeys_model_blocking_classification(tmp_path):
    from thesys_engine.workflow import save_proposal, authoritative_inputs

    assert cli(tmp_path, 'init') == 0
    m = load_methodology(ROOT)
    inputs = authoritative_inputs(tmp_path, m, m.stage('clarification'), tmp_path.name)

    save_proposal(
        tmp_path, 'clarification', 'test-project', 'mock', 'content',
        [{'question': 'Decisão material?', 'why': 'Necessária agora.', 'blocking': False}],
        inputs, m,
    )
    from thesys_engine.orchestration import _phase_action
    action = _phase_action(tmp_path, m, m.stage('clarification'))
    assert action.kind == 'human_review_stage'

    path = tmp_path / '.thesys' / 'proposals' / tmp_path.name / 'clarification.json'
    proposal = json.loads(path.read_text(encoding='utf-8-sig'))
    proposal['questions'][0]['blocking'] = True
    path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    action = _phase_action(tmp_path, m, m.stage('clarification'))
    assert action.kind == 'answer_stage_questions'


def test_executable_stages_do_not_use_generic_document_proposals(tmp_path):
    assert cli(tmp_path, 'init') == 0
    assert cli(tmp_path, 'config', 'set', 'agent_provider', 'mock') == 0
    assert cli(tmp_path, 'intent', 'create', 'Build a small internal tool.') == 0
    assert cli(tmp_path, 'next') == 0
    assert cli(tmp_path, 'discovery', 'accept') == 0
    assert cli(tmp_path, 'next') == 0
    assert cli(tmp_path, 'proposal', 'accept', 'governance') == 0
    assert cli(tmp_path, 'next') == 0
    assert cli(tmp_path, 'unit', 'proposal', 'accept') == 0

    m = load_methodology(ROOT)
    # Advance the document stages using the existing mock flow until Plan is current.
    for _ in range(100):
        action = next_action(tmp_path, m)
        if action.stage in {'plan', 'tasks'} and action.kind == 'human_review_stage':
            for path in sorted((tmp_path / '.thesys/proposals').rglob(f'{action.stage}.json')):
                proposal = json.loads(path.read_text(encoding='utf-8-sig'))
                if proposal.get('status') == 'proposed':
                    assert cli(tmp_path, 'proposal', 'accept', action.stage, '--unit', proposal['unit']) == 0
            if action.stage == 'tasks':
                break
        if action.kind == 'human_review_stage':
            for path in sorted((tmp_path / '.thesys/proposals').rglob(f'{action.stage}.json')):
                proposal = json.loads(path.read_text(encoding='utf-8-sig'))
                if proposal.get('status') == 'proposed':
                    assert cli(tmp_path, 'proposal', 'accept', action.stage, '--unit', proposal['unit']) == 0
        elif action.kind in {'propose_stage', 'propose', 'regenerate_stage', 'regenerate', 'propose_implementation', 'verify'}:
            assert cli(tmp_path, 'next') == 0
        elif action.kind == 'human_review':
            assert (cli(tmp_path, 'implementation', 'accept') if action.stage == 'implementation' else cli(tmp_path, 'proposal', 'accept', action.stage, '--unit', action.unit)) == 0
        else:
            raise AssertionError(action)
    else:
        raise AssertionError('Plan was not reached.')

    action = next_action(tmp_path, m)
    assert action.kind == 'propose_implementation'
    assert action.stage == 'implementation'
    assert not (tmp_path / '.thesys' / 'proposals' / tmp_path.name / 'implementation.json').exists()


def test_next_regenerates_current_governance_after_its_question_is_answered(tmp_path):
    assert cli(tmp_path, "init") == 0
    assert cli(tmp_path, "config", "set", "agent_provider", "mock") == 0
    assert cli(tmp_path, "intent", "create", "Build a distributor management system.") == 0
    assert cli(tmp_path, "next") == 0
    assert cli(tmp_path, "discovery", "accept") == 0
    assert cli(tmp_path, "next") == 0

    proposal_path = tmp_path / ".thesys" / "proposals" / "test-project" / "governance.json"
    data = json.loads(proposal_path.read_text(encoding="utf-8-sig"))
    data["questions"] = [{
        "id": "QST-001",
        "question": "Quem aprova exceções de governança?",
        "why": "A autoridade precisa ser definida.",
        "blocking": True,
    }]
    data["status"] = "proposed"
    proposal_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    assert cli(tmp_path, "question", "answer", "QST-001", "O gerente do projeto.") == 0
    assert json.loads(proposal_path.read_text(encoding="utf-8-sig"))["status"] == "needs_regeneration"

    assert cli(tmp_path, "next") == 0
    regenerated = json.loads(proposal_path.read_text(encoding="utf-8-sig"))
    assert regenerated["stage"] == "governance"
    assert regenerated["questions"] == []
    assert json.loads((tmp_path / ".thesys" / "proposals" / "test-project" / "intent.json").read_text(encoding="utf-8-sig"))["status"] != "needs_regeneration"


def test_discovery_cannot_be_restarted_after_intent_is_approved(tmp_path):
    assert cli(tmp_path, "init") == 0
    assert cli(tmp_path, "config", "set", "agent_provider", "mock") == 0
    assert cli(tmp_path, "intent", "create", "Build a system.") == 0
    assert cli(tmp_path, "next") == 0
    assert cli(tmp_path, "discovery", "accept") == 0

    import pytest
    with pytest.raises(Exception, match="Intent is already authoritative"):
        cli(tmp_path, "discovery", "propose", "--agent", "mock")
