import hashlib, json
from datetime import datetime, timezone
from .errors import ProjectError
from .io import read_text, write_text
from .registry import add_event, register_artifact, allocate_id
from .questions import allocate_question_id, validate_question_id
from .guidance import guidance_inputs, guidance_fingerprint

def sha(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()


def _project_scope_id(project):
    from .project import project_key
    return project_key(project)


def stage_unit(project, m, stage, unit):
    return _project_scope_id(project) if stage.config.get("scope") == "project" else unit


def proposal_path(project, stage_id, unit, methodology=None):
    stage = methodology.stage(stage_id) if methodology is not None else None
    stage_unit = _project_scope_id(project) if stage is None or stage.config.get("scope") == "project" else unit
    return project / ".thesys" / "proposals" / stage_unit / f"{stage_id}.json"


def answer_path(project): return project / ".thesys" / "answers.json"


def _load_answers(project):
    p = answer_path(project)
    return json.loads(read_text(p)) if p.is_file() else {}


def _clarification_history_for(project, stage_id, unit):
    """Return durable human clarification records for a stage and unit."""
    answers = _load_answers(project)
    return [
        {"id": qid, **record}
        for qid, record in answers.items()
        if isinstance(record, dict)
        and record.get("stage") == stage_id
        and record.get("unit") == unit
        and record.get("answer")
    ]


def answer_question(project, qid, answer):
    if not answer.strip():
        raise ProjectError("Answer cannot be empty.")
    validate_question_id(qid)
    data = _load_answers(project)
    record = {
        "answer": answer.strip(),
        "answered_at": datetime.now(timezone.utc).isoformat(),
    }
    found = False
    for path in _proposal_files(project):
        try:
            proposal = json.loads(read_text(path))
        except (json.JSONDecodeError, OSError):
            continue
        for question in proposal.get("questions", []):
            if question.get("id") != qid:
                continue
            found = True
            record.update({
                "question": question.get("question", ""),
                "why": question.get("why", ""),
                "blocking": bool(question.get("blocking", True)),
                "stage": proposal.get("stage"),
                "unit": proposal.get("unit"),
                "proposal_id": proposal.get("proposal_id"),
            })
            proposal["status"] = "needs_regeneration"
            write_text(path, json.dumps(proposal, ensure_ascii=False, indent=2) + "\n")
            break
        if found:
            break
    if not found:
        raise ProjectError(f"Question not found: {qid}")
    data[qid] = record
    write_text(answer_path(project), json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    add_event(project, "question-answered", qid, {"answer_sha256": sha(answer.strip())})
    return data[qid]


def _proposal_files(project):
    yield from (project / ".thesys" / "proposals").glob("*/*.json")

def load_proposal(project, stage_id, unit, methodology=None):
    p = proposal_path(project, stage_id, unit, methodology)
    if not p.is_file(): raise ProjectError(f"Proposal not found for stage '{stage_id}'. Generate it first.")
    try: return json.loads(read_text(p))
    except json.JSONDecodeError as exc: raise ProjectError(f"Invalid proposal: {p}") from exc




def proposal_inputs(project, m, stage, unit):
    """Return the complete current input snapshot for a proposal."""
    return {
        "authoritative": authoritative_inputs(project, m, stage, unit),
        "guidance": guidance_inputs(project, m, stage, unit),
    }


def _normalize_proposal_inputs(project, m, stage, unit, inputs):
    if m is None:
        return inputs or {}
    if isinstance(inputs, dict) and "authoritative" in inputs and "guidance" in inputs:
        return inputs
    # Preserve compatibility for internal callers/tests that supply only the
    # authoritative-input map; guidance is still captured at persistence time.
    return {"authoritative": inputs or {}, "guidance": guidance_inputs(project, m, stage, unit)}

def save_proposal(project, stage_id, unit, provider, content, questions, inputs, methodology=None, metadata=None):
    stage_unit = _project_scope_id(project) if methodology is None or methodology.stage(stage_id).config.get("scope") == "project" else unit
    path = proposal_path(project, stage_id, unit, methodology)
    old = {}
    if path.is_file():
        try:
            old = json.loads(read_text(path))
        except (json.JSONDecodeError, OSError):
            old = {}

    history = _clarification_history_for(project, stage_id, stage_unit)
    answered_ids = {record.get("id") for record in history}
    previous = {
        question.get("id"): question
        for question in old.get("questions", [])
        if isinstance(question.get("id"), str)
    }
    normalized = []
    reserved_ids: set[str] = set()

    for raw_question in questions or []:
        question = {
            "question": str(raw_question.get("question", "")).strip(),
            "why": str(raw_question.get("why", "")).strip(),
            "blocking": raw_question.get("blocking"),
        }
        if not question["question"]:
            raise ProjectError("Generated clarification question cannot be empty.")
        if not question["why"]:
            raise ProjectError("Generated clarification question must explain why it matters.")
        if not isinstance(question["blocking"], bool):
            raise ProjectError("Generated clarification question 'blocking' must be a boolean.")

        question_id = None
        for previous_id, previous_question in previous.items():
            if previous_id in answered_ids:
                continue
            if _question_similarity(question["question"], previous_question.get("question", "")) >= 0.62:
                question_id = previous_id
                break

        if question_id is None:
            question_id = allocate_question_id(project, reserved_ids)

        validate_question_id(question_id)
        if question_id in reserved_ids:
            raise ProjectError(f"Duplicate clarification question ID generated: {question_id}")
        reserved_ids.add(question_id)
        normalized.append({"id": question_id, **question})

    stage_definition = methodology.stage(stage_id) if methodology is not None else None
    inputs = _normalize_proposal_inputs(project, methodology, stage_definition, stage_unit, inputs)
    fp = sha(json.dumps(inputs, ensure_ascii=False, sort_keys=True))
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "2",
        "proposal_id": "PROP-" + sha(fp + stage_id + stage_unit + str(datetime.now(timezone.utc).timestamp()))[:12].upper(),
        "stage": stage_id,
        "unit": stage_unit,
        "provider": provider,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_fingerprint": fp,
        "status": "proposed",
        "questions": normalized,
        "clarification_history": history,
        "content": content.strip(),
    }
    if metadata:
        payload.update(metadata)
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    add_event(
        project,
        "ai-proposal-created",
        f"{stage_id}:{stage_unit}",
        {"provider": provider, "input_fingerprint": fp, "question_count": len(normalized)},
    )
    return path

def proposal_questions(project, proposal):
    answers = _load_answers(project)
    return [q for q in proposal.get("questions", []) if q.get("blocking", True) and q.get("id") not in answers]


def proposal_is_stale(project, m, stage_id, unit, proposal):
    """Return whether a persisted proposal no longer matches its current inputs."""
    if stage_id == "intent" and m.stage(stage_id).action == "discovery":
        from .intents import read_intent_input
        from .guidance import guidance_inputs
        inputs = {
            "authoritative": {
                "intent_input": read_intent_input(project),
                "answers": _load_answers(project),
                "project_template": (project / ".thesys/project.yaml").read_text(encoding="utf-8"),
            },
            "guidance": guidance_inputs(project, m, m.stage(stage_id), _project_scope_id(project)),
        }
    else:
        stage = m.stage(stage_id)
        inputs = proposal_inputs(project, m, stage, unit)
    return proposal.get("input_fingerprint") != sha(json.dumps(inputs, ensure_ascii=False, sort_keys=True))


def _work_unit_keys(project):
    from .project import work_units
    return [u["key"] for u in work_units(project)]


def _dependency_targets(project, m, stage, unit, dep):
    dep_stage = m.stage(dep)
    if stage.config.get("aggregate_units") and dep_stage.config.get("scope") != "project":
        return [(dep, key) for key in _work_unit_keys(project)]
    if stage.config.get("scope") == "project" or dep_stage.config.get("scope") == "project":
        return [(dep, _project_scope_id(project))]
    return [(dep, unit)]


def _artifact_path(m, project, stage, unit):
    return m.artifact_path(project, stage, stage_unit(project, m, stage, unit))


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
    from .project import has_child_units, scope_info, project_key
    if stage.config.get("scope") != "project":
        if not has_child_units(project) and unit == project_key(project):
            pass
        else:
            try:
                scope_info(project, unit)
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


def accept_proposal(project, m, stage_id, unit=None):
    unit = unit or _project_scope_id(project)
    stage = m.stage(stage_id)
    # Stage-specific execution is selected by lifecycle action, not by a hidden
    # stage ID branch. This keeps the lifecycle definition authoritative.
    if stage.action == "units":
        from .unit_proposals import accept_unit_proposal
        artifact = accept_unit_proposal(project, m)
        from .gates import approve
        prop = load_proposal(project, stage_id, unit, m)
        approve(project, m, stage_id, unit, proposal_id=prop["proposal_id"] if "proposal_id" in prop else None)
        prop["status"] = "accepted"
        prop["accepted_at"] = datetime.now(timezone.utc).isoformat()
        write_text(proposal_path(project, stage_id, unit, m), json.dumps(prop, ensure_ascii=False, indent=2) + "\n")
        return artifact
    # Discovery is a project-level composite proposal: its authoritative input
    # fingerprint includes the human Intent input, answered questions and the
    # project template, and its acceptance materializes both Intent and Context.
    # Keep that contract in one place instead of applying the generic artifact
    # dependency fingerprint (which is empty for the discovery stage).
    if stage_id == "intent" and m.stage(stage_id).action == "discovery":
        from .intents import accept_discovery
        return accept_discovery(project, m)[0]
    p = load_proposal(project, stage_id, unit, m)
    if p.get("stage") != stage_id: raise ProjectError("Proposal stage mismatch.")
    if p.get('status') not in {'proposed'}: raise ProjectError('Proposal is not current; regenerate it before approval.')
    if proposal_questions(project, p): raise ProjectError("Proposal has unanswered blocking questions. Answer them and regenerate the proposal before approval.")
    inputs = proposal_inputs(project, m, stage, unit)
    if p.get("input_fingerprint") != sha(json.dumps(inputs, ensure_ascii=False, sort_keys=True)):
        raise ProjectError("Proposal is stale because authoritative upstream context changed. Regenerate the proposal.")
    if not p.get("content", "").strip(): raise ProjectError("Proposal has no content.")
    target = _artifact_path(m, project, stage, unit)
    if not target: raise ProjectError(f"Stage '{stage_id}' is executable and must use its execution command.")
    target.parent.mkdir(parents=True, exist_ok=True)
    write_text(target, p["content"].rstrip() + '\n')
    from .gates import approve
    approve(project, m, stage_id, unit, proposal_id=p["proposal_id"])
    p["status"] = "accepted"
    p["accepted_at"] = datetime.now(timezone.utc).isoformat()
    write_text(proposal_path(project, stage_id, unit, m), json.dumps(p, ensure_ascii=False, indent=2) + "\n")
    return target


def show_proposal(project, stage_id, unit=None, methodology=None):
    unit = unit or _project_scope_id(project)
    return load_proposal(project, stage_id, unit, methodology)
