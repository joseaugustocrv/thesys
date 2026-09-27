from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import re

from .errors import ProjectError, ThesysError
from .io import read_text, write_text
from .intents import intent_digest, read_intent
from .project import create_unit, unit_info


@dataclass(frozen=True)
class UnitProposal:
    key: str
    name: str
    scope: str
    rationale: str
    unit_type: str = "capability"
    parent: str = "default"
    dependencies: tuple[str, ...] = ()


def proposal_dir(project):
    return project / ".thesys" / "proposals" / "engineering-units"


def proposal_path(project):
    return proposal_dir(project) / "proposal.json"


def slug(value):
    value = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return value[:64]


def _validate(items):
    if not items:
        raise ThesysError("Engineering unit proposal contains no units.")
    keys = set()
    allowed_types={"system","domain","capability","epic","module","service","feature","change","defect","migration","security-remediation","architecture-initiative","technical-debt","platform-change"}
    for item in items:
        if not re.fullmatch(r"[a-z][a-z0-9-]{1,63}", item.key):
            raise ThesysError(f"Invalid engineering unit key: {item.key}")
        if item.key in keys:
            raise ThesysError(f"Duplicate engineering unit key: {item.key}")
        keys.add(item.key)
        if not item.name.strip() or not item.scope.strip() or not item.rationale.strip():
            raise ThesysError(f"Engineering unit proposal is incomplete: {item.key}")
        if item.parent == item.key or item.key in item.dependencies:
            raise ThesysError(f"Engineering unit cannot depend on itself: {item.key}")
        if item.unit_type not in allowed_types:
            raise ThesysError(f"Unsupported engineering unit type: {item.unit_type}")

    # A proposal is a graph, not merely a list. Reject cycles before acceptance
    # so a malformed hierarchy can never make the acceptance loop ambiguous.
    parents={item.key:item.parent for item in items if item.parent in keys}
    for key in parents:
        seen=set(); current=key
        while current in parents:
            if current in seen:
                raise ThesysError(f"Engineering unit parent hierarchy contains a cycle at: {current}")
            seen.add(current); current=parents[current]

    dependencies={item.key:set(item.dependencies) & keys for item in items}
    colors={key:0 for key in dependencies}  # 0=unvisited, 1=active, 2=complete
    def visit(key):
        if colors[key] == 1:
            raise ThesysError(f"Engineering unit dependency graph contains a cycle at: {key}")
        if colors[key] == 2:
            return
        colors[key]=1
        for dependency in dependencies[key]:
            visit(dependency)
        colors[key]=2
    for key in dependencies:
        visit(key)


def write_proposal(project, provider, items):
    _validate(items)
    d = proposal_dir(project); d.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "1",
        "status": "proposed",
        "provider": provider,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_intent": "engineering/intent/intent.md",
        "intent_sha256": intent_digest(project),
        "engineering_units": [
            {"key": x.key, "name": x.name, "scope": x.scope, "rationale": x.rationale,
             "type": x.unit_type, "parent": x.parent, "dependencies": list(x.dependencies)}
            for x in items
        ],
    }
    write_text(proposal_path(project), json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return proposal_path(project)


def read_proposal(project):
    path = proposal_path(project)
    if not path.is_file():
        raise ProjectError("Engineering unit proposal not found. Run 'thesys unit propose' first.")
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise ProjectError("Engineering unit proposal is invalid JSON.") from exc
    items = [UnitProposal(
        key=x.get("key",""), name=x.get("name",""), scope=x.get("scope",""),
        rationale=x.get("rationale",""), unit_type=x.get("type","capability"),
        parent=x.get("parent","default"), dependencies=tuple(x.get("dependencies",[]))
    ) for x in data.get("engineering_units",[])]
    _validate(items)
    return data, items


def _capability_lines(intent):
    lines = intent.splitlines(); in_section=False; values=[]
    headings=("capabilities","expected capabilities","in scope","scope")
    for line in lines:
        stripped=line.strip()
        if stripped.startswith("## "):
            in_section=stripped[3:].strip().lower() in headings
            continue
        if not in_section:
            continue
        if re.match(r"^(?:[-*]|\d+\.)\s+", stripped):
            value=re.sub(r"^(?:[-*]|\d+\.)\s+", "", stripped).strip()
            if value and not value.startswith("["):
                values.append(value.rstrip("."))
    return values


class MockUnitAgent:
    name="mock"
    def propose_units(self, intent):
        items=[]
        for value in _capability_lines(intent):
            key=slug(value)
            if not key: continue
            items.append(UnitProposal(key, value, value + ".", "The capability is explicitly stated in the Intent."))
        if not items:
            items=[UnitProposal("project-scope","Project Scope","The coherent scope described by the authoritative Intent.","The Intent does not expose a sufficiently explicit capability decomposition for a more specific proposal.","capability")]
        return items


class OpenAIUnitAgent:
    name="openai"
    def __init__(self, client=None):
        if client is not None:
            self.client=client
        else:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise ThesysError("The OpenAI SDK is not installed. Reinstall Thesys with: python -m pip install -e .") from exc
            key=os.getenv("OPENAI_API_KEY")
            if not key: raise ThesysError("OPENAI_API_KEY is not configured.")
            self.client=OpenAI(api_key=key)
        self.model=os.getenv("THESYS_OPENAI_MODEL","gpt-5.6-luna")

    def propose_units(self, intent):
        schema={"type":"object","properties":{"engineering_units":{"type":"array","items":{"type":"object","properties":{
            "key":{"type":"string"},"name":{"type":"string"},"scope":{"type":"string"},"rationale":{"type":"string"},
            "type":{"type":"string"},"parent":{"type":"string"},"dependencies":{"type":"array","items":{"type":"string"}}
        },"required":["key","name","scope","rationale","type","parent","dependencies"],"additionalProperties":False}}},"required":["engineering_units"],"additionalProperties":False}
        instructions=("Propose Engineering Units from the authoritative Intent. Units are coherent scopes used to organize engineering work; they are not lifecycle stages and not automatically architecture boundaries. "
                      "Propose only units justified by the Intent. Do not invent requirements, technologies, APIs, architecture or business decisions. Prefer a small number of coherent units. Return a non-authoritative proposal for human review.")
        try:
            response=self.client.responses.create(model=self.model,instructions=instructions,input="Authoritative Intent:\n\n"+intent,text={"format":{"type":"json_schema","name":"thesys_engineering_unit_proposal","strict":True,"schema":schema}})
        except Exception as exc:
            raise ThesysError(f"OpenAI request failed: {exc}") from exc
        try: data=json.loads(response.output_text)
        except (json.JSONDecodeError,TypeError) as exc: raise ThesysError("OpenAI returned an invalid engineering unit proposal.") from exc
        items=[]
        for x in data.get("engineering_units",[]):
            key=slug(x.get("key","")); parent=slug(x.get("parent","default")) or "default"
            deps=tuple(slug(v) for v in x.get("dependencies",[]))
            items.append(UnitProposal(key,x.get("name","").strip(),x.get("scope","").strip(),x.get("rationale","").strip(),x.get("type","capability"),parent,deps))
        _validate(items)
        return items


def _intent_is_currently_approved(project):
    approvals = project / ".thesys" / "approvals.json"
    if not approvals.is_file():
        return False
    try:
        data=json.loads(read_text(approvals))
    except json.JSONDecodeError:
        return False
    approval=data.get("approvals",{}).get("intent:default")
    return bool(approval and approval.get("sha256") == intent_digest(project))


def generate_unit_proposal(project, provider="openai"):
    if not _intent_is_currently_approved(project):
        raise ProjectError("Engineering unit proposals require the current Intent to be human-approved first.")
    intent = read_intent(project)
    if proposal_path(project).is_file():
        data,_=read_proposal(project)
        if data.get("status")=="accepted": raise ProjectError("Engineering unit proposal has already been accepted.")
        raise ProjectError("An engineering unit proposal already exists; review or accept it before generating another.")
    agent = MockUnitAgent() if provider=="mock" else OpenAIUnitAgent() if provider=="openai" else None
    if agent is None: raise ThesysError(f"Unknown unit proposal agent: {provider}")
    return write_proposal(project,agent.name,agent.propose_units(intent))


def accept_unit_proposal(project, methodology):
    data, items=read_proposal(project)
    if data.get("status")!="proposed": raise ProjectError("Only a proposed engineering unit proposal can be accepted.")
    if data.get("intent_sha256") != intent_digest(project):
        raise ProjectError("Engineering unit proposal is stale because the authoritative Intent changed. Generate a new proposal.")
    existing={p.stem for p in (project/".thesys"/"units").glob("*.json")}
    for item in items:
        if item.key in existing: raise ProjectError(f"Engineering unit already exists: {item.key}")
    keys={x.key for x in items}
    for item in items:
        if item.parent!="default" and item.parent not in keys and item.parent not in existing:
            raise ProjectError(f"Engineering unit '{item.key}' references unknown parent: {item.parent}")
        unknown=[d for d in item.dependencies if d not in keys and d not in existing]
        if unknown: raise ProjectError(f"Engineering unit '{item.key}' references unknown dependencies: {', '.join(unknown)}")
    created=[]; remaining=list(items)
    try:
        while remaining:
            progressed=False
            for item in remaining[:]:
                if item.parent!="default" and item.parent in keys and item.parent not in existing:
                    if item.parent not in {x.key for x in remaining}: continue
                path=create_unit(project,item.key,item.name,item.scope,item.unit_type,item.parent,methodology,dependencies=list(item.dependencies))
                created.append(path); existing.add(item.key); remaining.remove(item); progressed=True
            if not progressed: raise ProjectError("Engineering unit proposal contains an unresolved parent hierarchy.")
    except Exception:
        for path in created: path.unlink(missing_ok=True)
        raise
    data["status"]="accepted"; data["accepted_at"]=datetime.now(timezone.utc).isoformat()
    write_text(proposal_path(project),json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    return created
