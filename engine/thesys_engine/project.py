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


def _project_metadata(project, methodology, template, name, key):
    return {
        "id": "PRJ-" + uuid.uuid4().hex[:12].upper(),
        "key": key,
        "name": name,
        "template": template.id,
        "kind": template.kind,
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

    if not (meta/"units"/"default.json").exists():
        create_unit(project,"default",project_name,selected.root_scope,selected.root_unit_type,None,methodology)

    # Project creation establishes only system metadata. No engineering artifact is
    # authoritative until an AI proposal is explicitly accepted by a human.
    add_event(project,"project-initialized",methodology.name,{"version":methodology.version,"template":selected.id})


def project_info(project):
    path=project/".thesys"/"project.yaml"
    if not path.is_file():
        raise ProjectError(f"Thesys project not initialized: {project}")
    return _read_simple_yaml(path)


def config(project):
    p=project/".thesys"/"config.yaml"
    if not p.is_file(): return {}
    return _read_simple_yaml(p)


def set_config(project,key,value):
    c=config(project); c[key]=value; write_text(project/".thesys"/"config.yaml", _write_yaml(c))


def create_unit(project,key,name,scope="",unit_type="feature",parent="default",methodology=None,dependencies=None):
    if not re_key(key): raise ProjectError("Unit key must start with a lowercase letter and contain lowercase letters, numbers, or hyphens.")
    if key == "default": parent=None
    if parent and not (project/".thesys"/"units"/f"{parent}.json").is_file(): raise ProjectError(f"Parent engineering unit not found: {parent}")
    p=project/".thesys"/"units"/f"{key}.json"
    if p.exists(): raise ProjectError(f"Engineering unit already exists: {key}")
    payload={"key":key,"name":name,"scope":scope,"type":unit_type,"parent":parent,"dependencies":dependencies or [],"source_intent":"engineering/intent/intent.md"}
    write_text(p,json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
    if methodology is None:
        from .methodology import load_methodology
        methodology=load_methodology(Path(__file__).resolve().parents[2])
    add_event(project,"unit-created",key,{"type":unit_type,"parent":parent,"source_intent":"engineering/intent/intent.md"})
    return p


def re_key(key): return bool(key) and key[0].islower() and all(c.islower() or c.isdigit() or c=="-" for c in key)

def unit_info(project,key):
    p=project/".thesys"/"units"/f"{key}.json"
    if not p.is_file(): raise ProjectError(f"Engineering unit not found: {key}")
    return json.loads(read_text(p))
