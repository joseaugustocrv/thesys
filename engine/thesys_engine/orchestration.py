import json
from dataclasses import dataclass
from pathlib import Path

from .errors import ProjectError
from .gates import status
from .project import work_targets, project_key
from .io import read_text
from .workflow import proposal_path, proposal_questions, proposal_is_stale


@dataclass(frozen=True)
class NextAction:
    kind: str
    stage: str | None = None
    unit: str | None = None
    reason: str = ""
    proposal: Path | None = None


def _proposal_state(project, methodology, stage_id, unit):
    path = proposal_path(project, stage_id, unit, methodology)
    if not path.is_file():
        return None, None
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise ProjectError(f"Invalid proposal: {path}") from exc
    return path, data


def _human_review_or_block(project, methodology, stage_id, unit):
    path, proposal = _proposal_state(project, methodology, stage_id, unit)
    if not proposal:
        return None
    if proposal.get("status") == "accepted":
        return None
    if proposal.get("status") == "needs_regeneration" or proposal_is_stale(project, methodology, stage_id, unit, proposal):
        return NextAction("regenerate", stage_id, unit, "The current proposal no longer matches its authoritative upstream inputs.", path)
    if proposal_questions(project, proposal):
        return NextAction("answer_questions", stage_id, unit, "Blocking questions remain unanswered.", path)
    return NextAction("human_review", stage_id, unit, "A current AI proposal is waiting for human approval.", path)


def _targets(project, stage):
    if stage.config.get("scope") == "project":
        return [project_key(project)]
    return [u["key"] for u in work_targets(project)]


def _stage_action(project, methodology, stage):
    """Return the next action for one lifecycle stage across all targets.

    Regeneration and blocking clarification always take precedence over a
    different Unit that merely has a current proposal awaiting review.
    """
    targets = _targets(project, stage)
    proposals = []
    for unit in targets:
        path, proposal = _proposal_state(project, methodology, stage.id, unit)
        if proposal and proposal.get("status") == "accepted":
            continue
        proposals.append((unit, path, proposal))

    for unit, path, proposal in proposals:
        if proposal and (proposal.get("status") == "needs_regeneration" or proposal_is_stale(project, methodology, stage.id, unit, proposal)):
            return NextAction("regenerate_stage", stage.id, project_key(project), f"One or more {stage.id} proposals no longer match authoritative inputs.")

    for unit, path, proposal in proposals:
        if proposal and proposal_questions(project, proposal):
            return NextAction("answer_stage_questions", stage.id, project_key(project), f"Blocking questions remain unanswered in stage '{stage.id}'.")

    for unit, path, proposal in proposals:
        if proposal:
            return NextAction("human_review_stage", stage.id, unit, f"The {stage.id} stage has proposals waiting for human review.", path)

    if stage.action == "verify":
        return NextAction("verify", stage.id, targets[0], "Run the configured verification command and generate the verification proposal.")
    if stage.action == "implementation":
        return NextAction("propose_implementation", stage.id, targets[0], "Generate the implementation proposal from approved engineering artifacts.")
    return NextAction("propose_stage", stage.id, project_key(project), f"Generate the {stage.id} stage proposal for all applicable Engineering Units or the Project root when no decomposition exists.")


def next_action(project, methodology, unit=None):
    """Find the next actionable lifecycle transition without implicit approval."""
    st = status(project, methodology, unit)
    intent_input = project / "engineering/intent/input.md"

    if not intent_input.is_file() and st.get("intent", {}).get("status") == "missing":
        return NextAction("human_input", "intent", project_key(project), "Create the project's Intent before AI discovery can begin.")

    intent_status = st.get("intent", {}).get("status")
    if intent_status == "needs_revalidation":
        return NextAction("regenerate", "intent", project_key(project), "The authoritative Intent is stale because its human guidance or discovery inputs changed.")
    if intent_status not in {"approved", "completed"}:
        review = _human_review_or_block(project, methodology, "intent", project_key(project))
        if review:
            return review
        if intent_status in {"missing", "input_received"}:
            return NextAction("propose_discovery", "intent", project_key(project), "The Intent input is ready for AI discovery.")
        if intent_status == "questions_pending":
            return NextAction("answer_questions", "intent", project_key(project), "Blocking discovery questions remain unanswered.")

    # The methodology order is canonical. Dependencies decide readiness; phases
    # only group stages for navigation and reporting.
    for stage in methodology.stages:
        if stage.id == "intent":
            continue
        current = st.get(stage.id, {}).get("status")
        if current in {"approved", "completed", "not_applicable"}:
            continue
        if current == "needs_revalidation":
            return NextAction("regenerate_stage", stage.id, project_key(project), f"Stage '{stage.id}' is stale because its upstream context or human guidance changed.")
        if current == "blocked":
            review = _human_review_or_block(project, methodology, stage.id, project_key(project) if stage.config.get("scope") == "project" else unit)
            if review:
                return review
            return NextAction("blocked", stage.id, project_key(project), f"Stage '{stage.id}' is blocked or requires revalidation.")

        # Evaluate all applicable targets through the stage-level action. This
        # keeps stale proposals ahead of unrelated current reviews.
        action = _stage_action(project, methodology, stage)
        if action:
            return action

    return NextAction("complete", None, unit or project_key(project), "All lifecycle stages are current for the selected project scope.")


def _phase_action(project, methodology, stage):
    """Backward-compatible private alias for callers of the 0.4 runtime API."""
    return _stage_action(project, methodology, stage)
