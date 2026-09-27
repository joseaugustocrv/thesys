import json
from datetime import datetime, timezone
from pathlib import Path
from .io import read_text, write_text


def _path(project):
    return project / ".thesys" / "registry.json"


def _load(project):
    p = _path(project)
    return json.loads(read_text(p)) if p.is_file() else {"artifacts": {}, "relations": [], "events": []}


def _save(project, data):
    write_text(_path(project), json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def now():
    return datetime.now(timezone.utc).isoformat()


def register_artifact(project, artifact_id, artifact_type, path, unit, status="draft", authority="human"):
    data = _load(project)
    data["artifacts"][artifact_id] = {
        "id": artifact_id, "type": artifact_type, "path": str(path), "unit": unit,
        "status": status, "authority": authority, "updated_at": now()
    }
    _save(project, data)


def add_relation(project, source, relation, target, source_version=None):
    data = _load(project)
    item = {"source": source, "relation": relation, "target": target, "created_at": now()}
    if source_version: item["source_version"] = source_version
    if item not in data["relations"]: data["relations"].append(item)
    _save(project, data)


def add_event(project, kind, subject, details=None):
    data = _load(project)
    data["events"].append({"kind": kind, "subject": subject, "details": details or {}, "created_at": now()})
    _save(project, data)


def get(project):
    return _load(project)


def allocate_id(project, prefix):
    data = _load(project)
    nums=[]
    for key in data["artifacts"]:
        if key.startswith(prefix + "-"):
            try: nums.append(int(key.split("-")[-1]))
            except ValueError: pass
    n=max(nums, default=0)+1
    return f"{prefix}-{n:03d}"
