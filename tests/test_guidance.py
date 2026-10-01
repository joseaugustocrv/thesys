import hashlib
import json
from pathlib import Path

from thesys_cli.main import main
from thesys_engine.gates import status
from thesys_engine.methodology import load_methodology
from thesys_engine.guidance import add_guidance, guidance_inputs

ROOT = Path(__file__).parents[1]


def cli(project, *args):
    return main([*args, "--path", str(project)])


def _advance_to_requirements(tmp_path):
    assert cli(tmp_path, "init") == 0
    assert cli(tmp_path, "config", "set", "agent_provider", "mock") == 0
    assert cli(tmp_path, "intent", "create", "Build a finance platform.") == 0
    assert cli(tmp_path, "next") == 0
    assert cli(tmp_path, "discovery", "accept") == 0
    assert cli(tmp_path, "next") == 0
    assert cli(tmp_path, "proposal", "accept", "governance") == 0
    assert cli(tmp_path, "next") == 0
    assert cli(tmp_path, "unit", "proposal", "accept") == 0
    assert cli(tmp_path, "next") == 0
    for unit in ("financial-records", "financial-monitoring"):
        # The mock decomposition used by the test may differ by project, so
        # advance whichever context proposal was generated.
        proposal = tmp_path / ".thesys" / "proposals" / unit / "context.json"
        if proposal.is_file():
            assert cli(tmp_path, "proposal", "accept", "context", "--unit", unit) == 0


def test_guidance_is_optional_and_persisted(tmp_path):
    assert cli(tmp_path, "init") == 0
    m = load_methodology(ROOT)
    path = add_guidance(tmp_path, "requirements", "test-project", "directive", "Use BRL in the MVP.", "Currency", methodology=m)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    assert data["type"] == "directive"
    assert data["status"] == "active"
    assert data["created_by"] == "human"
    assert guidance_inputs(tmp_path, m, m.stage("requirements"), "test-project")["GUD-001"]["content"] == "Use BRL in the MVP."


def test_guidance_invalidates_stage_and_downstream_approved_baselines(tmp_path):
    assert cli(tmp_path, "init") == 0
    assert cli(tmp_path, "config", "set", "agent_provider", "mock") == 0
    assert cli(tmp_path, "intent", "create", "Build a finance platform.") == 0
    assert cli(tmp_path, "discovery", "propose", "--agent", "mock") == 0
    assert cli(tmp_path, "discovery", "accept") == 0
    assert cli(tmp_path, "generate", "governance", "--agent", "mock") == 0
    assert cli(tmp_path, "proposal", "accept", "governance") == 0
    assert cli(tmp_path, "generate", "engineering-units", "--agent", "mock") == 0
    assert cli(tmp_path, "proposal", "accept", "engineering-units") == 0
    assert cli(tmp_path, "generate", "context", "--agent", "mock") == 0
    assert cli(tmp_path, "proposal", "accept", "context") == 0
    assert cli(tmp_path, "generate", "requirements", "--agent", "mock") == 0
    assert cli(tmp_path, "proposal", "accept", "requirements") == 0

    m = load_methodology(ROOT)
    assert status(tmp_path, m)["context"]["status"] == "approved"
    assert status(tmp_path, m)["requirements"]["status"] == "approved"

    assert cli(tmp_path, "guidance", "add", "context", "directive", "The MVP uses manual records only.", "--title", "MVP boundary") == 0

    current = status(tmp_path, m)
    assert current["context"]["status"] == "needs_revalidation"
    assert current["requirements"]["status"] == "needs_revalidation"

    # The guidance is part of the current input fingerprint.
    proposal_path = tmp_path / ".thesys" / "proposals" / "test-project" / "context.json"
    assert proposal_path.is_file()
    proposal = json.loads(proposal_path.read_text(encoding="utf-8-sig"))
    assert proposal["status"] == "accepted"
    expected = {
        "authoritative": {
            "intent": (tmp_path / "engineering" / "intent" / "intent.md").read_text(encoding="utf-8-sig"),
            "governance": (tmp_path / "engineering" / "governance" / "governance.md").read_text(encoding="utf-8-sig"),
            "engineering-units": (tmp_path / "engineering" / "units" / "engineering-units.md").read_text(encoding="utf-8-sig"),
        },
        "guidance": guidance_inputs(tmp_path, m, m.stage("context"), "test-project"),
    }
    current_fingerprint = hashlib.sha256(json.dumps(expected, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    assert proposal["input_fingerprint"] != current_fingerprint
    from thesys_engine.workflow import proposal_is_stale
    assert proposal_is_stale(tmp_path, m, "context", "test-project", proposal)


def test_guidance_is_forward_scoped_to_same_unit_and_project_stages(tmp_path):
    assert cli(tmp_path, "init") == 0
    assert cli(tmp_path, "config", "set", "agent_provider", "mock") == 0
    assert cli(tmp_path, "intent", "create", "Build a finance platform.") == 0
    assert cli(tmp_path, "next") == 0
    assert cli(tmp_path, "discovery", "accept") == 0
    assert cli(tmp_path, "unit", "create", "financial-records", "Financial Records", "--type", "capability") == 0
    assert cli(tmp_path, "unit", "create", "financial-monitoring", "Financial Monitoring", "--type", "capability") == 0
    m = load_methodology(ROOT)
    add_guidance(tmp_path, "context", "financial-records", "review-note", "Keep this unit manual.", methodology=m)
    add_guidance(tmp_path, "governance", "test-project", "directive", "Preserve privacy boundaries.", methodology=m)

    records = guidance_inputs(tmp_path, m, m.stage("requirements"), "financial-records")
    monitoring = guidance_inputs(tmp_path, m, m.stage("requirements"), "financial-monitoring")
    assert {x["content"] for x in records.values()} == {"Keep this unit manual.", "Preserve privacy boundaries."}
    assert {x["content"] for x in monitoring.values()} == {"Preserve privacy boundaries."}
    system = guidance_inputs(tmp_path, m, m.stage("system-architecture"), "test-project")
    assert {x["content"] for x in system.values()} == {"Keep this unit manual.", "Preserve privacy boundaries."}



def test_guidance_inputs_preserve_guidance_id(tmp_path):
    assert cli(tmp_path, "init") == 0
    m = load_methodology(ROOT)
    add_guidance(tmp_path, "governance", "test-project", "directive", "Keep the Engine authoritative.", methodology=m)
    guidance = guidance_inputs(tmp_path, m, m.stage("governance"), "test-project")
    assert guidance["GUD-001"]["id"] == "GUD-001"


def test_documentation_guidance_is_direct_not_propagated_display_context(tmp_path):
    assert cli(tmp_path, "init") == 0
    m = load_methodology(ROOT)
    add_guidance(tmp_path, "governance", "test-project", "directive", "Governance-only direction.", methodology=m)
    from thesys_engine.documentation import _artifact_items, _related
    # The Engine still propagates governance guidance into downstream inputs.
    downstream = guidance_inputs(tmp_path, m, m.stage("engineering-units"), "test-project")
    assert "GUD-001" in downstream
    # Documentation, however, exposes only guidance directly attached to the viewed artifact.
    add_guidance(tmp_path, "engineering-units", "test-project", "directive", "Engineering-units direction.", methodology=m)
    items = _artifact_items(tmp_path)
    units = next((item for item in items if item.get("stage") == "engineering-units"), None)
    if units:
        guidance = {item["id"] for item in units["human_guidance"]}
        assert "GUD-001" not in guidance
        assert "GUD-002" in guidance

def test_guidance_text_attachment_is_hashed_and_shown_in_documentation(tmp_path):
    assert cli(tmp_path, "init") == 0
    assert cli(tmp_path, "config", "set", "agent_provider", "mock") == 0
    assert cli(tmp_path, "intent", "create", "Build a finance platform.") == 0
    assert cli(tmp_path, "next") == 0
    assert cli(tmp_path, "discovery", "accept") == 0
    assert cli(tmp_path, "next") == 0
    assert cli(tmp_path, "proposal", "accept", "governance") == 0
    assert cli(tmp_path, "next") == 0
    assert cli(tmp_path, "unit", "proposal", "accept") == 0
    assert cli(tmp_path, "next") == 0
    source = tmp_path / "reference.md"
    source.write_text("# Finance rule\n\nUse BRL only.\n", encoding="utf-8")
    assert cli(tmp_path, "guidance", "add", "requirements", "reference", "Business reference", "--title", "Business reference", "--file", str(source)) == 0
    assert cli(tmp_path, "next") == 0
    assert cli(tmp_path, "proposal", "accept", "context") == 0
    assert cli(tmp_path, "next") == 0
    record = json.loads(next((tmp_path / ".thesys" / "guidance").glob("GUD-*.json")).read_text(encoding="utf-8-sig"))
    assert record["attachment"]["filename"] == "reference.md"
    assert len(record["attachment"]["sha256"]) == 64
    html = (tmp_path / ".thesys" / "docs" / "index.html").read_text(encoding="utf-8-sig")
    assert "Business reference" in html
    assert "reference.md" in html


def test_guidance_at_intent_marks_intent_and_downstream_stale(tmp_path):
    assert cli(tmp_path, "init") == 0
    assert cli(tmp_path, "config", "set", "agent_provider", "mock") == 0
    assert cli(tmp_path, "intent", "create", "Build a system.") == 0
    assert cli(tmp_path, "next") == 0
    assert cli(tmp_path, "discovery", "accept") == 0
    assert cli(tmp_path, "next") == 0
    assert cli(tmp_path, "proposal", "accept", "governance") == 0
    m = load_methodology(ROOT)
    assert status(tmp_path, m)["intent"]["status"] == "approved"
    assert cli(tmp_path, "guidance", "add", "intent", "directive", "Preserve the original product boundary.", "--title", "Intent boundary") == 0
    current = status(tmp_path, m)
    assert current["intent"]["status"] == "needs_revalidation"
    assert current["governance"]["status"] == "needs_revalidation"
    assert cli(tmp_path, "next") == 0
    proposal = json.loads((tmp_path / ".thesys" / "proposals" / "test-project" / "intent.json").read_text(encoding="utf-8-sig"))
    assert proposal["status"] == "proposed"
