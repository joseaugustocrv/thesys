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
class Stage:
    id: str
    name: str
    artifact: str|None
    template: str|None
    approval: bool
    depends_on: tuple[str,...]
    action: str
    config: dict

@dataclass(frozen=True)
class Methodology:
    name: str
    version: str
    language: str
    root: Path
    definition: Path
    stages: tuple[Stage,...]
    rules: dict
    catalog: dict
    def stage(self, stage_id):
        for s in self.stages:
            if s.id==stage_id: return s
        raise MethodologyError(f"Unknown lifecycle stage: {stage_id}.")
    def artifact_path(self, project, stage, unit="default"):
        if not stage.artifact: return None
        return project / stage.artifact.format(unit=unit)

    def action_stages(self, action):
        return tuple(s for s in self.stages if s.action == action)

    def execution_path(self, project, stage, unit="default"):
        return project / ".thesys" / "executions" / f"{stage.id}-{unit}.json"

def load_methodology(repo: Path) -> Methodology:
    definition=repo/"methodology"/"definition"/"lifecycle.md"
    if not definition.is_file(): raise MethodologyError(f"Methodology definition not found: {definition}")
    data=parse_front_matter(read_text(definition)); meta=data.get("thesys",{}); lc=data.get("lifecycle",{})
    stages=[]
    for raw in lc.get("stages",[]):
        if not isinstance(raw,dict): raise MethodologyError("Each lifecycle stage must be a mapping.")
        stages.append(Stage(str(raw["id"]),str(raw.get("name",raw["id"])),raw.get("artifact"),raw.get("template"),raw.get("approval",False) is True or raw.get("approval")=="required",tuple(raw.get("depends_on",[]) or []),str(raw.get("action","document")),dict(raw.get("config",{}) or {})))
    if not stages: raise MethodologyError("Methodology defines no stages.")
    ids={s.id for s in stages}
    if len(ids)!=len(stages): raise MethodologyError("Lifecycle stage IDs must be unique.")
    for s in stages:
        for d in s.depends_on:
            if d not in ids: raise MethodologyError(f"Stage {s.id} depends on unknown stage {d}.")
    catalog_path=repo/"methodology"/"definition"/"catalog.json"
    catalog=json.loads(read_text(catalog_path)) if catalog_path.is_file() else {}
    return Methodology(str(meta.get("methodology","thesys")),str(meta.get("version","0")),str(meta.get("language","en-US")),repo,definition,tuple(stages),dict(lc.get("rules",{})),catalog)
