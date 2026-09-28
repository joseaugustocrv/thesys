import hashlib, json
from datetime import datetime, timezone
from .errors import ProjectError
from .io import read_text, write_text
from .registry import add_event, register_artifact, allocate_id

def sha(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()


def stage_unit(m, stage, unit):
    return "default" if stage.config.get("scope") == "project" else unit


def proposal_path(project, stage_id, unit, methodology=None):
    stage_unit = "default" if methodology is None or methodology.stage(stage_id).config.get("scope") == "project" else unit
    return project / ".thesys" / "proposals" / stage_unit / f"{stage_id}.json"


def answer_path(project): return project / ".thesys" / "answers.json"


def _load_answers(project):
    p = answer_path(project)
    return json.loads(read_text(p)) if p.is_file() else {}


def answer_question(project, qid, answer):
    if not answer.strip(): raise ProjectError("Answer cannot be empty.")
    data = _load_answers(project)
    data[qid] = {"answer": answer.strip(), "answered_at": datetime.now(timezone.utc).isoformat()}
    write_text(answer_path(project), json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    for f in (project / ".thesys/proposals").glob("*/*.json"):
        try:
            p = json.loads(read_text(f))
            if any(q.get("id") == qid for q in p.get("questions", [])):
                p["status"] = "needs_regeneration"
                write_text(f, json.dumps(p, ensure_ascii=False, indent=2) + "\n")
        except (json.JSONDecodeError, OSError):
            continue
    add_event(project, "question-answered", qid, {"answer_sha256": sha(answer.strip())})
    return data[qid]


def load_proposal(project, stage_id, unit, methodology=None):
    p = proposal_path(project, stage_id, unit, methodology)
    if not p.is_file(): raise ProjectError(f"Proposal not found for stage '{stage_id}'. Generate it first.")
    try: return json.loads(read_text(p))
    except json.JSONDecodeError as exc: raise ProjectError(f"Invalid proposal: {p}") from exc


def save_proposal(project, stage_id, unit, provider, content, questions, inputs, methodology=None):
    stage_unit = "default" if methodology is None or methodology.stage(stage_id).config.get("scope") == "project" else unit
    normalized = []
    for q in questions or []:
        normalized.append({"id": q.get("id") or "QST-" + str(len(normalized) + 1).zfill(3), "question": q.get("question", "").strip(), "why": q.get("why", "").strip(), "blocking": bool(q.get("blocking", True))})
    fp = sha(json.dumps(inputs, ensure_ascii=False, sort_keys=True))
    p = proposal_path(project, stage_id, unit, methodology)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema": "2", "proposal_id": "PROP-" + sha(fp + stage_id + stage_unit)[:12].upper(), "stage": stage_id, "unit": stage_unit, "provider": provider, "created_at": datetime.now(timezone.utc).isoformat(), "input_fingerprint": fp, "status": "proposed", "questions": normalized, "content": content.strip()}
    write_text(p, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    add_event(project, "ai-proposal-created", f"{stage_id}:{stage_unit}", {"provider": provider, "input_fingerprint": fp, "question_count": len(normalized)})
    return p


def proposal_questions(project, proposal):
    answers = _load_answers(project)
    return [q for q in proposal.get("questions", []) if q.get("blocking", True) and q.get("id") not in answers]


def _work_unit_keys(project):
    from .project import work_units
    return [u["key"] for u in work_units(project)]


def _dependency_targets(project, m, stage, unit, dep):
    dep_stage = m.stage(dep)
    if stage.config.get("aggregate_units") and dep_stage.config.get("scope") != "project":
        return [(dep, key) for key in _work_unit_keys(project)]
    if stage.config.get("scope") == "project" or dep_stage.config.get("scope") == "project":
        return [(dep, "default")]
    return [(dep, unit)]


def _artifact_path(m, project, stage, unit):
    return m.artifact_path(project, stage, stage_unit(m, stage, unit))


def _materialize_authoritative_content(content):
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.casefold().startswith('**status:**'):
            value = stripped[len('**status:**'):].strip().casefold()
            if value in {'draft', 'proposed', 'non-authoritative', 'non authoritative'}:
                line = '**Status:** Authoritative'
        elif stripped.casefold().startswith('status:'):
            value = stripped[len('status:'):].strip().casefold()
            if value in {'draft', 'proposed', 'non-authoritative', 'non authoritative'}:
                line = 'Status: Authoritative'
        elif stripped.casefold().startswith('**status da proposta:**'):
            line = '**Status da proposta:** Autoritativa.'
        lines.append(line)
    return '\n'.join(lines).rstrip() + '\n'


def authoritative_inputs(project, m, stage, unit):
    data = {}
    for dep_id in stage.depends_on:
        for dep_name, dep_unit in _dependency_targets(project, m, stage, unit, dep_id):
            dep_stage = m.stage(dep_name)
            p = m.artifact_path(project, dep_stage, dep_unit)
            if p and p.is_file():
                key = dep_name if not stage.config.get("aggregate_units") else f"{dep_name}:{dep_unit}"
                data[key] = read_text(p)
    return data


def can_propose(project, m, stage, unit):
    from .gates import status
    from .project import has_child_units, unit_info
    if stage.config.get("scope") != "project" and unit == "default" and has_child_units(project):
        raise ProjectError("The default system unit is a container once child Engineering Units exist. Run this stage for a specific Engineering Unit.")
    if stage.config.get("scope") != "project":
        try:
            unit_info(project, unit)
        except ProjectError:
            raise ProjectError(f"Engineering unit not found: {unit}")
    st = status(project, m, unit)
    if stage.config.get("aggregate_units"):
        from .gates import _stage_current, _dependency_targets
        cache = {}
        missing = [d for d in stage.depends_on if not all(_stage_current(project, m, d, dep_unit, cache=cache) for _, dep_unit in _dependency_targets(project, m, stage, unit, d))]
    else:
        missing = [d for d in stage.depends_on if st.get(d, {}).get("status") not in {"approved", "completed"}]
    if missing: raise ProjectError(f"Stage '{stage.id}' cannot be proposed before: {', '.join(missing)}")


def accept_proposal(project, m, stage_id, unit="default"):
    stage = m.stage(stage_id)
    p = load_proposal(project, stage_id, unit, m)
    if p.get("stage") != stage_id: raise ProjectError("Proposal stage mismatch.")
    if p.get('status') not in {'proposed'}: raise ProjectError('Proposal is not current; regenerate it before approval.')
    if proposal_questions(project, p): raise ProjectError("Proposal has unanswered blocking questions. Answer them and regenerate the proposal before approval.")
    inputs = authoritative_inputs(project, m, stage, unit)
    if p.get("input_fingerprint") != sha(json.dumps(inputs, ensure_ascii=False, sort_keys=True)):
        raise ProjectError("Proposal is stale because authoritative upstream context changed. Regenerate the proposal.")
    if not p.get("content", "").strip(): raise ProjectError("Proposal has no content.")
    target = _artifact_path(m, project, stage, unit)
    if not target: raise ProjectError(f"Stage '{stage_id}' is executable and must use its execution command.")
    target.parent.mkdir(parents=True, exist_ok=True)
    write_text(target, _materialize_authoritative_content(p["content"]))
    from .gates import approve
    approve(project, m, stage_id, unit, proposal_id=p["proposal_id"])
    p["status"] = "accepted"
    p["accepted_at"] = datetime.now(timezone.utc).isoformat()
    write_text(proposal_path(project, stage_id, unit, m), json.dumps(p, ensure_ascii=False, indent=2) + "\n")
    return target


def show_proposal(project, stage_id, unit="default", methodology=None):
    return load_proposal(project, stage_id, unit, methodology)
