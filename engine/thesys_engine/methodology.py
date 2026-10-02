from dataclasses import dataclass
from pathlib import Path
import re
from .errors import MethodologyError
from .io import read_text
import json

_KEY = re.compile(r"^[A-Za-z0-9_-]+$")

def scalar(value):
    value=value.strip()
    if value in ("null", "~"): return None
    if value.lower() == "true": return True
    if value.lower() == "false": return False
    if value.startswith("[") and value.endswith("]"):
        body=value[1:-1].strip()
        if not body: return []
        return [scalar(x) for x in body.split(",")]
    if len(value)>=2 and value[0] in "\"'" and value[-1]==value[0]:
        return value[1:-1]
    return value

def parse_front_matter(text: str) -> dict:
    text=text.replace("\ufeff", "")
    if not text.startswith("---\n"):
        raise MethodologyError("Methodology definition must start with YAML front matter.")
    end=text.find("\n---", 4)
    if end < 0:
        raise MethodologyError("Methodology definition has an unclosed front matter block.")
    lines=text[4:end].splitlines()
    root={}
    stack=[(-1, root)]
    i=0
    while i<len(lines):
        raw=lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i+=1; continue
        indent=len(raw)-len(raw.lstrip(" "))
        s=raw.strip()
        while stack and indent<=stack[-1][0]: stack.pop()
        parent=stack[-1][1]
        if s.startswith("- "):
            if not isinstance(parent,list): raise MethodologyError(f"Invalid list indentation: {raw}")
            item=s[2:].strip()
            if ":" in item:
                k,v=item.split(":",1); obj={k.strip(): scalar(v)}; parent.append(obj); stack.append((indent,obj))
            else: parent.append(scalar(item))
            i+=1; continue
        if ":" not in s: raise MethodologyError(f"Unsupported methodology syntax: {raw}")
        k,v=s.split(":",1); k=k.strip(); v=v.strip()
        if not _KEY.match(k): raise MethodologyError(f"Invalid methodology key: {k}")
        if v: parent[k]=scalar(v)
        else:
            j=i+1
            while j<len(lines) and not lines[j].strip(): j+=1
            child=[] if j<len(lines) and lines[j].lstrip().startswith("- ") else {}
            parent[k]=child; stack.append((indent,child))
        i+=1
    return root

@dataclass(frozen=True)
class Phase:
    id: str
    name: str
    stage_ids: tuple[str, ...]


@dataclass(frozen=True)
class Stage:
    id: str
    name: str
    artifact: str | None
    template: str | None
    approval: bool
    depends_on: tuple[str, ...]
    action: str
    config: dict
    phase_id: str = ""


@dataclass(frozen=True)
class Methodology:
    name: str
    version: str
    language: str
    root: Path
    definition: Path
    phases: tuple[Phase, ...]
    stages: tuple[Stage, ...]
    rules: dict
    catalog: dict

    def stage(self, stage_id):
        for s in self.stages:
            if s.id == stage_id:
                return s
        raise MethodologyError(f"Unknown lifecycle stage: {stage_id}.")

    def phase(self, phase_id):
        for phase in self.phases:
            if phase.id == phase_id:
                return phase
        raise MethodologyError(f"Unknown lifecycle phase: {phase_id}.")

    def phase_for_stage(self, stage_id):
        stage = self.stage(stage_id)
        return self.phase(stage.phase_id)

    def artifact_path(self, project, stage, unit=None):
        if unit is None:
            from .project import project_key
            unit = project_key(project)
        if not stage.artifact:
            return None
        return project / stage.artifact.format(unit=unit)

    def action_stages(self, action):
        return tuple(s for s in self.stages if s.action == action)

    def execution_path(self, project, stage, unit=None):
        if unit is None:
            from .project import project_key
            unit = project_key(project)
        return project / ".thesys" / "executions" / f"{stage.id}-{unit}.json"

def _resolve_methodology_root(repo: Path) -> Path:
    """Resolve source-tree or installed-package methodology resources."""
    candidates = (
        repo,
        repo / "bundle",
        repo / "thesys_engine" / "bundle",
    )
    for root in candidates:
        if (root / "methodology" / "definition" / "lifecycle.md").is_file():
            return root
    searched = ", ".join(str(root / "methodology" / "definition" / "lifecycle.md") for root in candidates)
    raise MethodologyError(f"Methodology definition not found. Searched: {searched}")


def _build_stage(raw, phase_id):
    if not isinstance(raw, dict):
        raise MethodologyError("Each lifecycle stage must be a mapping.")
    return Stage(
        id=str(raw["id"]),
        name=str(raw.get("name", raw["id"])),
        artifact=raw.get("artifact"),
        template=raw.get("template"),
        approval=raw.get("approval", False) is True or raw.get("approval") == "required",
        depends_on=tuple(raw.get("depends_on", []) or []),
        action=str(raw.get("action", "document")),
        config=dict(raw.get("config", {}) or {}),
        phase_id=phase_id,
    )


def load_methodology(repo: Path) -> Methodology:
    root = _resolve_methodology_root(repo)
    definition = root / "methodology" / "definition" / "lifecycle.md"
    data = parse_front_matter(read_text(definition))
    meta = data.get("thesys", {})
    lc = data.get("lifecycle", {})

    phases = []
    stages = []
    phase_defs = lc.get("phases") or []
    if phase_defs:
        for raw_phase in phase_defs:
            if not isinstance(raw_phase, dict):
                raise MethodologyError("Each lifecycle phase must be a mapping.")
            phase_id = str(raw_phase.get("id", "")).strip()
            if not phase_id:
                raise MethodologyError("Lifecycle phases require an id.")
            phase_name = str(raw_phase.get("name", phase_id))
            phase_stages = []
            for raw_stage in raw_phase.get("stages", []) or []:
                stage = _build_stage(raw_stage, phase_id)
                phase_stages.append(stage.id)
                stages.append(stage)
            phases.append(Phase(phase_id, phase_name, tuple(phase_stages)))
    else:
        # Backward compatibility for external methodologies using the 0.4 flat form.
        flat = []
        for raw in lc.get("stages", []) or []:
            stage = _build_stage(raw, "default")
            flat.append(stage)
            stages.append(stage)
        phases = [Phase("default", "Lifecycle", tuple(s.id for s in flat))]

    if not stages:
        raise MethodologyError("Methodology defines no lifecycle stages.")
    phase_ids = {p.id for p in phases}
    if len(phase_ids) != len(phases):
        raise MethodologyError("Lifecycle phase IDs must be unique.")
    stage_ids = {s.id for s in stages}
    if len(stage_ids) != len(stages):
        raise MethodologyError("Lifecycle stage IDs must be unique.")
    if set().union(*(set(p.stage_ids) for p in phases)) != stage_ids:
        raise MethodologyError("Every lifecycle stage must belong to exactly one phase.")

    positions = {stage.id: index for index, stage in enumerate(stages)}
    for stage in stages:
        if stage.phase_id not in phase_ids:
            raise MethodologyError(f"Stage {stage.id} references unknown lifecycle phase {stage.phase_id}.")
        for dep in stage.depends_on:
            if dep not in stage_ids:
                raise MethodologyError(f"Stage {stage.id} depends on unknown stage {dep}.")
            if positions[dep] >= positions[stage.id]:
                raise MethodologyError(f"Stage {stage.id} depends on stage {dep}, which is not earlier in the canonical lifecycle order.")

    catalog_path = root / "methodology" / "definition" / "catalog.json"
    catalog = json.loads(read_text(catalog_path)) if catalog_path.is_file() else {}
    return Methodology(
        str(meta.get("methodology", "thesys")),
        str(meta.get("version", "0")),
        str(meta.get("language", "en-US")),
        root,
        definition,
        tuple(phases),
        tuple(stages),
        dict(lc.get("rules", {})),
        catalog,
    )
