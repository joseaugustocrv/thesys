import hashlib, json
from datetime import datetime, timezone
from .io import read_text, write_text
from .errors import ProjectError
from .registry import add_event, register_artifact, allocate_id
from .workflow import stage_unit, _dependency_targets, proposal_path
from .guidance import guidance_fingerprint


def _state(project):
    p = project / ".thesys" / "approvals.json"
    return json.loads(read_text(p)) if p.is_file() else {"approvals": {}}


def _save(project, state): write_text(project / ".thesys" / "approvals.json", json.dumps(state, ensure_ascii=False, indent=2) + "\n")


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def _key(project, stage, unit):
    from .project import project_key
    return f"{stage.id}:{project_key(project) if stage.config.get('scope') == 'project' else unit}"


def _dep_fingerprint(project, m, stage, unit):
    snap = {}
    for dep_id in stage.depends_on:
        for dep_name, dep_unit in _dependency_targets(project, m, stage, unit, dep_id):
            dep = m.stage(dep_name)
            p = m.artifact_path(project, dep, dep_unit)
            if p and p.is_file():
                key = dep_name if not stage.config.get("aggregate_units") else f"{dep_name}:{dep_unit}"
                snap[key] = digest(p)
    # Human guidance is a durable non-authoritative input to the proposal
    # stream. Its fingerprint participates in gate freshness so adding guidance
    # to an approved stage invalidates that stage and all downstream stages.
    snap["__human_guidance__"] = guidance_fingerprint(project, m, stage, unit)
    return snap


def _stage_current(project, m, stage_id, unit, seen=None, cache=None):
    if seen is None: seen = set()
    if cache is None: cache = {}
    key = (stage_id, unit)
    if key in cache: return cache[key]
    if key in seen: return False
    seen = seen | {key}
    s = m.stage(stage_id)
    su = stage_unit(project, m, s, unit)
    if s.id == "engineering-units" and _legacy_engineering_units_current(project, m):
        cache[key] = True
        return True
    if s.artifact is None:
        ex = m.execution_path(project, s, su)
        if not ex.is_file(): cache[key] = False; return False
        try: data = json.loads(read_text(ex))
        except json.JSONDecodeError: cache[key] = False; return False
        expected = hashlib.sha256(json.dumps(_dep_fingerprint(project, m, s, unit), sort_keys=True).encode()).hexdigest()
        if data.get('input_fingerprint') != expected: cache[key] = False; return False
        ok = all(_stage_current(project, m, dep, dep_unit, seen, cache) for dep in s.depends_on for _, dep_unit in _dependency_targets(project, m, s, unit, dep))
        cache[key] = ok
        return ok
    state = _state(project)
    a = state['approvals'].get(_key(project, s, unit))
    p = m.artifact_path(project, s, su)
    if not a or not p or not p.is_file() or a.get('sha256') != digest(p): cache[key] = False; return False
    if a.get('dependencies', {}) != _dep_fingerprint(project, m, s, unit): cache[key] = False; return False
    ok = all(_stage_current(project, m, dep, dep_unit, seen, cache) for dep in s.depends_on for _, dep_unit in _dependency_targets(project, m, s, unit, dep))
    cache[key] = ok
    return ok


def _approval_current(project, m, stage_id, unit, seen=None):
    return _stage_current(project, m, stage_id, unit, seen)


def _deps_match(project, m, stage, unit, approval):
    if approval.get('dependencies', {}) != _dep_fingerprint(project, m, stage, unit): return False
    cache={}
    return all(_stage_current(project, m, dep, dep_unit, cache=cache) for dep in stage.depends_on for _, dep_unit in _dependency_targets(project, m, stage, unit, dep))


def _aggregate_unit_statuses(statuses):
    """Collapse child-unit lifecycle states into the project/container view."""
    values = [entry.get("status") for entry in statuses.values()]
    if not values:
        return "missing"
    if all(value == "approved" for value in values):
        return "approved"
    if any(value == "needs_revalidation" for value in values):
        return "needs_revalidation"
    if any(value == "needs_regeneration" for value in values):
        return "needs_regeneration"
    if any(value == "blocked" for value in values):
        return "blocked"
    if any(value == "questions_pending" for value in values):
        return "questions_pending"
    if all(value == "proposed" for value in values):
        return "proposed"
    if all(value == "missing" for value in values):
        return "missing"
    return "partial"


def _legacy_engineering_units_current(project, m):
    """Recognize the accepted 0.4 Engineering Units proposal during migration.

    The compatibility path is read-only: it never manufactures approval. It only
    preserves a previously explicit human acceptance while the new authoritative
    Unit Map is materialized by a later lifecycle mutation.
    """
    legacy = project / ".thesys" / "proposals" / "engineering-units" / "proposal.json"
    if not legacy.is_file():
        return False
    try:
        data = json.loads(read_text(legacy))
    except (OSError, json.JSONDecodeError):
        return False
    if data.get("status") != "accepted":
        return False
    from .project import project_key
    intent = m.stage("intent")
    governance = m.stage("governance")
    if not _stage_current(project, m, intent.id, project_key(project)) or not _stage_current(project, m, governance.id, project_key(project)):
        return False
    units = data.get("engineering_units", [])
    return all((project / ".thesys" / "units" / f"{item.get('key')}.json").is_file() for item in units)


def status(project, m, unit=None):
    if unit is None:
        from .project import project_key
        unit = project_key(project)
    state = _state(project)
    result = {}
    current_cache = {}
    from .workflow import proposal_path, proposal_questions
    from .project import has_child_units, work_units
    # The Project root is the authoritative project-scoped entity. When child
    # Engineering Units exist, unit-scoped stages are aggregated into that view.
    child_units = has_child_units(project)
    from .project import project_key
    if unit == project_key(project) and child_units:
        child_results = {u["key"]: status(project, m, u["key"]) for u in work_units(project)}
        for s in m.stages:
            if s.config.get("scope") == "project":
                continue
            child_statuses = {key: child_state[s.id] for key, child_state in child_results.items()}
            result[s.id] = {"status": _aggregate_unit_statuses(child_statuses)}
        # Continue below only for project-scoped stages.
        project_stages = [s for s in m.stages if s.config.get("scope") == "project"]
    else:
        project_stages = []
    stages_to_process = project_stages if unit == project_key(project) and child_units else list(m.stages)
    for s in stages_to_process:
        if s.id == "engineering-units" and _legacy_engineering_units_current(project, m):
            result[s.id] = {"status": "approved", "legacy": True}
            continue
        su = stage_unit(project, m, s, unit)
        if s.action == "discovery":
            p = m.artifact_path(project, s, project_key(project))
            if p and p.is_file():
                a = state["approvals"].get(_key(project, s, unit))
                current_guidance = guidance_fingerprint(project, m, s, project_key(project))
                result[s.id] = {"status": "approved" if a and a.get("sha256") == digest(p) and a.get("dependencies", {}).get("__human_guidance__") == current_guidance else "needs_revalidation"}
            elif (project / "engineering/intent/input.md").is_file():
                pp = proposal_path(project, "intent", project_key(project), m)
                result[s.id] = {"status": ("needs_regeneration" if json.loads(read_text(pp)).get("status") == "needs_regeneration" else ("questions_pending" if proposal_questions(project, json.loads(read_text(pp))) else "proposed")) if pp.is_file() else "input_received"}
            else: result[s.id] = {"status": "missing"}
            continue
        if s.artifact is None:
            deps_ok = all(_stage_current(project, m, dep, dep_unit, cache=current_cache) for dep in s.depends_on for _, dep_unit in _dependency_targets(project, m, s, unit, dep))
            if not deps_ok: result[s.id] = {"status": "blocked"}; continue
            ex = m.execution_path(project, s, unit)
            if not ex.is_file(): result[s.id] = {"status": "ready"}; continue
            try: data = json.loads(read_text(ex))
            except json.JSONDecodeError: data = {}
            current = hashlib.sha256(json.dumps(_dep_fingerprint(project, m, s, unit), sort_keys=True).encode()).hexdigest()
            result[s.id] = {"status": "completed" if data.get("input_fingerprint") == current else "needs_revalidation"}; continue
        p = m.artifact_path(project, s, su)
        if s.config.get("aggregate_units"):
            deps_ok = all(_stage_current(project, m, dep, dep_unit, cache=current_cache) for dep in s.depends_on for _, dep_unit in _dependency_targets(project, m, s, unit, dep))
            if p and p.is_file() and not deps_ok:
                result[s.id] = {"status": "needs_revalidation"}
                continue
            if (not p or not p.is_file()) and not deps_ok:
                result[s.id] = {"status": "blocked"}
                continue
        if not p or not p.is_file():
            pp = proposal_path(project, s.id, unit, m)
            if pp.is_file():
                try:
                    prop = json.loads(read_text(pp)); result[s.id] = {"status": "needs_regeneration" if prop.get('status') == 'needs_regeneration' else ("questions_pending" if proposal_questions(project, prop) else "proposed")}
                except json.JSONDecodeError: result[s.id] = {"status": "proposed"}
            else: result[s.id] = {"status": "missing"}
            continue
        a = state["approvals"].get(_key(project, s, unit))
        if not a: result[s.id] = {"status": "pending_review"}; continue
        if a.get("sha256") != digest(p) or not _deps_match(project, m, s, unit, a): result[s.id] = {"status": "needs_revalidation"}; continue
        result[s.id] = {"status": "approved"}
    return result


def approve(project, m, stage_id, unit=None, proposal_id=None):
    if unit is None:
        from .project import project_key
        unit = project_key(project)
    s = m.stage(stage_id)
    if not s.approval: raise ProjectError(f"Stage '{stage_id}' does not require approval.")
    from .workflow import proposal_questions
    if proposal_id is None: raise ProjectError("Human approval is only valid for an existing AI proposal. Use 'thesys proposal accept'.")
    pp = proposal_path(project, stage_id, unit, m)
    if not pp.is_file(): raise ProjectError("AI proposal not found; approval cannot proceed.")
    prop = json.loads(read_text(pp))
    if prop.get("proposal_id") != proposal_id: raise ProjectError("Approval does not match the current AI proposal.")
    if proposal_questions(project, prop): raise ProjectError("Blocking questions remain unanswered.")
    p = m.artifact_path(project, s, stage_unit(project, m, s, unit))
    if not p or not p.is_file(): raise ProjectError(f"Authoritative artifact missing: {s.artifact}")
    st = status(project, m, unit)
    if s.config.get("aggregate_units"):
        current_cache = {}
        if not all(_stage_current(project, m, dep, dep_unit, cache=current_cache) for dep in s.depends_on for _, dep_unit in _dependency_targets(project, m, s, unit, dep)):
            raise ProjectError(f"Stage '{stage_id}' cannot be approved before all aggregated dependencies are current.")
    else:
        missing = [d for d in s.depends_on if st.get(d, {}).get("status") not in {"approved", "completed"}]
        if missing: raise ProjectError(f"Stage '{stage_id}' cannot be approved before: {', '.join(missing)}")
    state = _state(project); key = _key(project, s, unit); deps = _dep_fingerprint(project, m, s, unit)
    state["approvals"][key] = {"sha256": digest(p), "dependencies": deps, "proposal_id": proposal_id, "approved_at": datetime.now(timezone.utc).isoformat()}
    _save(project, state)
    prefix = s.config.get("artifact_prefix")
    if not prefix: raise ProjectError(f"No artifact prefix is defined for lifecycle stage '{stage_id}'.")
    aid = allocate_id(project, prefix)
    register_artifact(project, aid, prefix, p, stage_unit(project, m, s, unit), status="authoritative", authority="human")
    # Materialize lifecycle dependencies as traceability relations. The registry
    # must expose the same dependency graph used by the gate, not only the
    # approval fingerprint.
    from .registry import find_artifact_id_by_path, add_relation
    for dep_id in s.depends_on:
        for dep_name, dep_unit in _dependency_targets(project, m, s, unit, dep_id):
            dep_stage = m.stage(dep_name)
            dep_path = m.artifact_path(project, dep_stage, stage_unit(project, m, dep_stage, dep_unit))
            if dep_path and dep_path.is_file():
                target_id = find_artifact_id_by_path(project, dep_path)
                if target_id and target_id != aid:
                    add_relation(project, aid, "depends-on", target_id)
    if s.config.get("aggregate_relation"):
        from .registry import get, add_relation
        from .project import project_key
        for other_id, artifact in get(project).get("artifacts", {}).items():
            if artifact.get("type") == "ARC" and artifact.get("unit") != project_key(project) and other_id != aid:
                add_relation(project, aid, s.config.get("aggregate_relation"), other_id)
    add_event(project, "human-approved-ai-proposal", key, {"proposal_id": proposal_id, "dependencies": deps})


def next_stage(project, m, unit=None):
    if unit is None:
        from .project import project_key
        unit = project_key(project)
    st = status(project, m, unit)
    for s in m.stages:
        if st[s.id]["status"] not in {"approved", "completed"}: return s
    return None
