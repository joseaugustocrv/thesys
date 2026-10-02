from datetime import datetime, timezone
from pathlib import Path
import json
import re
import uuid

from .io import write_text, read_text
from .templates import load_template
from .errors import ProjectError
from .registry import add_event, register_artifact, allocate_id
from .project_templates import get_project_template


WORKSPACE_STATE_DIR = ".thesys-workspace"
ACTIVE_PROJECT_FILE = "active-project.yaml"
PROJECT_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")


def project_metadata_path(project):
    return project / ".thesys" / "project.yaml"


def is_project(path):
    return project_metadata_path(path).is_file()


def validate_project_key(key):
    if not PROJECT_KEY_PATTERN.fullmatch(key or ""):
        raise ProjectError("Project key must start with a lowercase letter and contain only lowercase letters, numbers, hyphens, or underscores (2-64 characters).")
    return key


def _workspace_state_path(workspace):
    return workspace / WORKSPACE_STATE_DIR / ACTIVE_PROJECT_FILE


def set_active_project(workspace, project):
    workspace = workspace.resolve()
    project = project.resolve()
    if is_project(workspace):
        raise ProjectError("Active-project selection must be performed from a project workspace, not from inside a project.")
    try:
        relative = project.relative_to(workspace)
    except ValueError as exc:
        raise ProjectError(f"Project must be inside the workspace: {project}") from exc
    if not is_project(project):
        raise ProjectError(f"Not a Thesys project: {project}")
    state = _workspace_state_path(workspace)
    state.parent.mkdir(parents=True, exist_ok=True)
    write_text(state, _write_yaml({"key": project_info(project).get("key", project.name), "path": str(relative)}))
    return project


def active_project(workspace):
    workspace = workspace.resolve()
    if is_project(workspace):
        return workspace
    state = _workspace_state_path(workspace)
    if not state.is_file():
        raise ProjectError(f"No active Thesys project selected for workspace: {workspace}. Create one with 'thesys project create' or select one with 'thesys project use <key>'.")
    data = _read_simple_yaml(state)
    raw = data.get("path") or data.get("key")
    if not raw:
        raise ProjectError(f"Active Thesys project state is invalid: {state}")
    target = (workspace / raw).resolve()
    try:
        target.relative_to(workspace)
    except ValueError as exc:
        raise ProjectError("Active project points outside the workspace.") from exc
    if not is_project(target):
        raise ProjectError(f"Active Thesys project no longer exists: {target}")
    return target


def resolve_project(path, key=None):
    path = Path(path).resolve()
    if key:
        validate_project_key(key)
        if is_project(path):
            raise ProjectError("A project key cannot be resolved from inside another project. Run the command from the project workspace or omit the key.")
        target = (path / key).resolve()
        try:
            target.relative_to(path)
        except ValueError as exc:
            raise ProjectError("Project path escapes the workspace.") from exc
        if not is_project(target):
            raise ProjectError(f"Thesys project not found: {target}")
        return target
    return active_project(path)



def project_key(project):
    """Return the canonical identity of the Project root entity."""
    return project_info(project).get("key") or project.resolve().name


def list_units(project):
    """Return only real Engineering Unit entities."""
    units_dir = project / ".thesys" / "units"
    result = []
    for path in sorted(units_dir.glob("*.json")):
        try:
            data = json.loads(read_text(path))
        except json.JSONDecodeError as exc:
            raise ProjectError(f"Invalid engineering unit metadata: {path}") from exc
        result.append(data)
    return result


def work_units(project):
    """Return real Engineering Units participating in unit-scoped work."""
    return list_units(project)


def work_targets(project):
    """Return lifecycle targets for unit-scoped stages.

    A project without Engineering Units uses the Project root itself as the
    single work target. Once Engineering Units exist, only those units are
    targeted. The Project is never materialized as a fake Engineering Unit.
    """
    units = list_units(project)
    if units:
        return units
    info = project_info(project)
    return [{
        "key": project_key(project),
        "name": info.get("name", project_key(project)),
        "scope": info.get("root_scope", "Project-wide scope"),
        "type": "project",
        "parent": None,
        "dependencies": [],
    }]


def has_child_units(project):
    return bool(list_units(project))


def ensure_project_within_workspace(project, workspace):
    project = Path(project).resolve()
    workspace = Path(workspace).resolve()
    if project == workspace:
        raise ProjectError("A Thesys project must be a child of the 'Thesys Projects' workspace, not the workspace itself.")
    try:
        project.relative_to(workspace)
    except ValueError as exc:
        raise ProjectError(f"Thesys projects must be created inside the workspace: {workspace}") from exc
    return project

def _project_metadata(project, methodology, template, name, key):
    return {
        "id": "PRJ-" + uuid.uuid4().hex[:12].upper(),
        "key": key,
        "name": name,
        "template": template.id,
        "kind": template.kind,
        "root_unit_type": template.root_unit_type,
        "root_scope": template.root_scope,
        "methodology": methodology.name,
        "methodology_version": methodology.version,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _write_yaml(data):
    lines=[]
    for key, value in data.items():
        if value is None:
            continue
        lines.append(f"{key}: {value}")
    return "\n".join(lines) + "\n"


def _read_simple_yaml(path):
    if not path.is_file():
        return {}
    result={}
    for line in read_text(path).splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            key,value=line.split(":",1)
            result[key.strip()]=value.strip()
    return result



def migrate_legacy_artifacts(project):
    """Move only previously registered Thesys artifacts from docs/ to engineering/.

    This is intentionally conservative: ordinary project documentation under
    docs/ is never moved. Only paths already recorded in the Thesys registry are
    eligible for migration.
    """
    registry_path = project / ".thesys" / "registry.json"
    if not registry_path.is_file():
        return []
    try:
        data = json.loads(read_text(registry_path))
    except json.JSONDecodeError as exc:
        raise ProjectError("Thesys registry is invalid JSON; legacy artifact migration was not performed.") from exc

    moved=[]
    for item in data.get("artifacts", {}).values():
        raw=item.get("path")
        if not raw:
            continue
        source=Path(raw)
        try:
            relative=source.resolve().relative_to(project.resolve())
        except ValueError:
            continue
        if not relative.parts or relative.parts[0] != "docs":
            continue
        target=project / "engineering" / Path(*relative.parts[1:])
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and target.resolve() != source.resolve():
                raise ProjectError(f"Cannot migrate legacy artifact because target already exists: {target}")
            source.replace(target)
            item["path"]=str(target)
            moved.append((source,target))

    if moved:
        write_text(registry_path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")

    # Keep project metadata generated by earlier versions coherent with the
    # new artifact root without rewriting historical event records.
    for unit_file in (project / ".thesys" / "units").glob("*.json"):
        try:
            unit=json.loads(read_text(unit_file))
        except json.JSONDecodeError:
            continue
        if unit.get("source_intent") == "docs/intent/intent.md":
            unit["source_intent"]="engineering/intent/intent.md"
            write_text(unit_file, json.dumps(unit, ensure_ascii=False, indent=2) + "\n")

    for proposal_file in (project / ".thesys" / "proposals").rglob("*.json"):
        try:
            proposal=json.loads(read_text(proposal_file))
        except json.JSONDecodeError:
            continue
        changed=False
        if proposal.get("source_intent") == "docs/intent/intent.md":
            proposal["source_intent"]="engineering/intent/intent.md"; changed=True
        if changed:
            write_text(proposal_file, json.dumps(proposal, ensure_ascii=False, indent=2) + "\n")
    return moved

def init_project(project, methodology, template=None, name=None, key=None):
    project = project.resolve()
    project.mkdir(parents=True, exist_ok=True)
    migrate_legacy_artifacts(project)
    selected = get_project_template(methodology.root, template)
    project_key = validate_project_key(key or project.name)
    project_name = name or project_key.replace("-", " ").replace("_", " ").title()

    meta=project/".thesys"
    meta.mkdir(parents=True,exist_ok=True)
    for d in ("proposals","units","evidence","changes","executions"):
        (meta/d).mkdir(exist_ok=True)
    for directory in selected.directories:
        if directory and directory not in {".thesys"}:
            (project/directory).mkdir(parents=True, exist_ok=True)

    project_meta=meta/"project.yaml"
    if not project_meta.exists():
        write_text(project_meta, _write_yaml(_project_metadata(project,methodology,selected,project_name,project_key)))
    config_path=meta/"config.yaml"
    if not config_path.exists():
        write_text(config_path, f"language: {methodology.language}\nagent_provider: {selected.agent_provider or 'openai'}\ntemplate: {selected.id}\n")

    if not (meta/"registry.json").exists():
        write_text(meta/"registry.json", json.dumps({"artifacts":{},"relations":[],"events":[]},indent=2)+"\n")
    if not (meta/"approvals.json").exists():
        write_text(meta/"approvals.json", json.dumps({"approvals":{}},indent=2)+"\n")

    _migrate_legacy_project_root(project, methodology)

    # Project creation establishes only system metadata. No engineering artifact is
    # authoritative until an AI proposal is explicitly accepted by a human.
    add_event(project,"project-initialized",project_key,{"version":methodology.version,"template":selected.id})


def project_info(project):
    path=project/".thesys"/"project.yaml"
    if not path.is_file():
        raise ProjectError(f"Thesys project not initialized: {project}")
    return _read_simple_yaml(path)


def config(project):
    p=project/".thesys"/"config.yaml"
    if not p.is_file(): return {}
    return _read_simple_yaml(p)


def project_language(project, fallback="en-US"):
    """Return the effective language configured for a project."""
    value=config(project).get("language")
    return value.strip() if value and value.strip() else fallback


def set_config(project,key,value):
    c=config(project); c[key]=value; write_text(project/".thesys"/"config.yaml", _write_yaml(c))


def create_unit(project,key,name,scope="",unit_type="feature",parent=None,methodology=None,dependencies=None):
    root = project_key(project)
    if not re_key(key):
        raise ProjectError("Unit key must start with a lowercase letter and contain lowercase letters, numbers, or hyphens.")
    if key == root:
        raise ProjectError("Engineering unit key cannot be the same as the Project root key.")
    if parent in (None, "", "default"):
        parent = root
    if parent == key:
        raise ProjectError("An Engineering Unit cannot be its own parent.")
    if parent != root and not (project/".thesys"/"units"/f"{parent}.json").is_file():
        raise ProjectError(f"Parent engineering unit not found: {parent}")
    p=project/".thesys"/"units"/f"{key}.json"
    if p.exists(): raise ProjectError(f"Engineering unit already exists: {key}")
    payload={"key":key,"name":name,"scope":scope,"type":unit_type,"parent":parent,"dependencies":dependencies or [],"source_intent":"engineering/intent/intent.md"}
    write_text(p,json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
    if methodology is None:
        from .methodology import load_methodology
        methodology=load_methodology(Path(__file__).resolve().parents[2])
    add_event(project,"unit-created",key,{"type":unit_type,"parent":parent,"source_intent":"engineering/intent/intent.md"})
    return p


def scope_info(project, key):
    """Return authoritative metadata for a lifecycle work target.

    The Project root is a valid target for unit-scoped lifecycle stages when no
    Engineering Units have been decomposed. It is not persisted as a Unit.
    """
    root = project_key(project)
    if key == root and not (project/".thesys"/"units"/f"{key}.json").is_file():
        info = project_info(project)
        return {
            "key": root,
            "name": info.get("name", root),
            "scope": info.get("root_scope", "Project-wide scope"),
            "type": "project",
            "parent": None,
            "dependencies": [],
        }
    return unit_info(project, key)


def _migrate_legacy_project_root(project, methodology):
    """Migrate the 0.5.0 synthetic ``default`` root to the Project entity.

    Migration is conservative and content-preserving. Project-scoped records and,
    when no child Units exist, legacy root unit-scoped records are moved to the
    canonical Project key. Existing child Units keep their identities while a
    legacy ``default`` parent is rewritten to the Project root.
    """
    root = project_key(project)
    units_dir = project / ".thesys" / "units"
    legacy = units_dir / "default.json"
    child_paths = [p for p in units_dir.glob("*.json") if p.stem != "default"]
    had_legacy_root = legacy.is_file()
    if had_legacy_root:
        try:
            legacy_data = json.loads(read_text(legacy))
        except json.JSONDecodeError:
            legacy_data = {}
    else:
        legacy_data = {}

    for path in child_paths:
        try:
            data = json.loads(read_text(path))
        except json.JSONDecodeError:
            continue
        if data.get("parent") == "default":
            data["parent"] = root
            write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")

    has_children = bool(child_paths)
    # Move authoritative/proposed unit-scoped artifacts from the old root only
    # when the project did not decompose. With child Units, those records were
    # container-era state and must not become authoritative work for the Project.
    for stage in methodology.stages:
        if not stage.artifact:
            continue
        if stage.config.get("scope") == "project" or not has_children:
            source = methodology.artifact_path(project, stage, "default")
            target = methodology.artifact_path(project, stage, root)
            if source and target and source.is_file() and source.resolve() != target.resolve():
                if target.exists():
                    raise ProjectError(f"Cannot migrate legacy artifact because target already exists: {target}")
                target.parent.mkdir(parents=True, exist_ok=True)
                source.replace(target)
        if stage.artifact is None and not has_children:
            source = methodology.execution_path(project, stage, "default")
            target = methodology.execution_path(project, stage, root)
            if source.is_file() and source.resolve() != target.resolve():
                if target.exists():
                    raise ProjectError(f"Cannot migrate legacy execution record because target already exists: {target}")
                target.parent.mkdir(parents=True, exist_ok=True)
                source.replace(target)

    proposals = project / ".thesys" / "proposals"
    legacy_dir = proposals / "default"
    if legacy_dir.is_dir():
        target = proposals / root
        target.mkdir(parents=True, exist_ok=True)
        project_stage_ids = {s.id for s in methodology.stages if s.config.get("scope") == "project"}
        unit_stage_ids = {s.id for s in methodology.stages if s.config.get("scope") != "project"}
        for path in list(legacy_dir.glob("*.json")):
            stage_id = path.stem
            if stage_id not in project_stage_ids and (has_children or stage_id not in unit_stage_ids):
                continue
            destination = target / path.name
            if destination.exists():
                raise ProjectError(f"Cannot migrate legacy proposal because target already exists: {destination}")
            path.replace(destination)
            try:
                data = json.loads(read_text(destination))
                data["unit"] = root
                write_text(destination, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
            except json.JSONDecodeError:
                pass
        if legacy_dir.exists() and not any(legacy_dir.iterdir()):
            legacy_dir.rmdir()

    answers_path = project / ".thesys" / "answers.json"
    if answers_path.is_file():
        try:
            answers = json.loads(read_text(answers_path)); changed = False
            for record in answers.values():
                if isinstance(record, dict) and record.get("unit") == "default":
                    record["unit"] = root; changed = True
            if changed:
                write_text(answers_path, json.dumps(answers, ensure_ascii=False, indent=2) + "\n")
        except json.JSONDecodeError:
            pass

    approvals_path = project / ".thesys" / "approvals.json"
    if approvals_path.is_file():
        try:
            approvals = json.loads(read_text(approvals_path)); changed = False
            for stage in methodology.stages:
                if stage.config.get("scope") == "project" or not has_children:
                    old_key = f"{stage.id}:default"
                    new_key = f"{stage.id}:{root}"
                    if old_key in approvals.get("approvals", {}) and new_key not in approvals["approvals"]:
                        approvals["approvals"][new_key] = approvals["approvals"].pop(old_key)
                        changed = True
            if changed:
                write_text(approvals_path, json.dumps(approvals, ensure_ascii=False, indent=2) + "\n")
        except json.JSONDecodeError:
            pass

    registry_path = project / ".thesys" / "registry.json"
    if registry_path.is_file():
        try:
            registry = json.loads(read_text(registry_path)); changed = False
            legacy_paths = set()
            canonical_paths = set()
            for stage in methodology.stages:
                if not stage.artifact:
                    continue
                legacy_path = methodology.artifact_path(project, stage, "default")
                canonical_path = methodology.artifact_path(project, stage, root)
                if legacy_path:
                    legacy_paths.add(str(legacy_path.resolve()))
                if canonical_path:
                    canonical_paths.add(str(canonical_path.resolve()))
            for artifact in registry.get("artifacts", {}).values():
                if artifact.get("unit") != "default":
                    continue
                raw = artifact.get("path", "")
                try:
                    resolved = str(Path(raw).resolve())
                except OSError:
                    resolved = raw
                if resolved in legacy_paths or resolved in canonical_paths or not has_children:
                    artifact["unit"] = root
                    if resolved in legacy_paths:
                        artifact["path"] = str(Path(raw).parent.parent / root / Path(raw).name) if not has_children else artifact.get("path")
                    changed = True
            if changed:
                write_text(registry_path, json.dumps(registry, ensure_ascii=False, indent=2) + "\n")
        except json.JSONDecodeError:
            pass

    if legacy.exists():
        legacy.unlink()

def re_key(key): return bool(key) and key[0].islower() and all(c.islower() or c.isdigit() or c=="-" for c in key)

def unit_info(project,key):
    p=project/".thesys"/"units"/f"{key}.json"
    if not p.is_file(): raise ProjectError(f"Engineering unit not found: {key}")
    return json.loads(read_text(p))
