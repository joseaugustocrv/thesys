from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import unicodedata

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


@dataclass(frozen=True)
class UnitProposalResult:
    decompose: bool
    units: tuple[UnitProposal, ...] = ()


def proposal_dir(project):
    return project / ".thesys" / "proposals" / "engineering-units"


def proposal_path(project):
    return proposal_dir(project) / "proposal.json"


def slug(value):
    value = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return value[:64]


ALLOWED_UNIT_TYPES = (
    "system", "domain", "capability", "epic", "module", "service", "feature",
    "change", "defect", "migration", "security-remediation",
    "architecture-initiative", "technical-debt", "platform-change",
)

_UNIT_TYPE_ALIASES = {
    "sistema": "system",
    "dominio": "domain",
    "capacidade": "capability",
    "epico": "epic",
    "modulo": "module",
    "servico": "service",
    "funcionalidade": "feature",
    "mudanca": "change",
    "defeito": "defect",
    "migracao": "migration",
    "remediacao-de-seguranca": "security-remediation",
    "iniciativa-de-arquitetura": "architecture-initiative",
    "divida-tecnica": "technical-debt",
    "mudanca-de-plataforma": "platform-change",
}

def canonical_unit_type(value):
    raw = str(value or "").strip().lower()
    if raw in ALLOWED_UNIT_TYPES:
        return raw
    normalized = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return _UNIT_TYPE_ALIASES.get(normalized, raw)


def _validate(items):
    if not items:
        raise ThesysError("Engineering unit proposal contains no units.")
    keys = set()
    allowed_types=set(ALLOWED_UNIT_TYPES)
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


def write_proposal(project, provider, items, decompose=True):
    _validate(items) if items else None
    if decompose and not items:
        raise ThesysError("Engineering unit proposal marked for decomposition but contains no units.")
    d = proposal_dir(project); d.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "1",
        "status": "proposed",
        "provider": provider,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_intent": "engineering/intent/intent.md",
        "intent_sha256": intent_digest(project),
        "decompose": bool(decompose),
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
        rationale=x.get("rationale",""), unit_type=canonical_unit_type(x.get("type","capability")),
        parent=x.get("parent","default"), dependencies=tuple(x.get("dependencies",[]))
    ) for x in data.get("engineering_units",[])]
    if data.get("decompose", bool(items)):
        _validate(items)
    elif items:
        raise ProjectError("Engineering unit proposal is inconsistent: units exist while decomposition is disabled.")
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
        seen=set()
        for value in _capability_lines(intent):
            key=slug(value)
            if not key or key in seen: continue
            seen.add(key)
            items.append(UnitProposal(key, value, value + ".", "The capability is explicitly stated in the Intent."))
        return UnitProposalResult(bool(items), tuple(items))


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
        schema={
            "type": "object",
            "properties": {
                "decompose": {"type": "boolean"},
                "engineering_units": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "key": {"type": "string"},
                            "name": {"type": "string"},
                            "scope": {"type": "string"},
                            "rationale": {"type": "string"},
                            "type": {"type": "string", "enum": list(ALLOWED_UNIT_TYPES)},
                            "parent": {"type": "string"},
                            "dependencies": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["key", "name", "scope", "rationale", "type", "parent", "dependencies"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["decompose", "engineering_units"],
            "additionalProperties": False,
        }
        instructions=("Propose Engineering Units from the authoritative Intent. First decide whether decomposition is justified by the complexity and scope explicitly established by the Intent. If the project is small enough to remain coherent as one system, set decompose=false and return an empty engineering_units array. If decomposition is justified, set decompose=true and propose only a small number of coherent units. Units are coherent scopes used to organize engineering work; they are not lifecycle stages and not automatically architecture boundaries. Do not invent requirements, technologies, APIs, architecture or business decisions. The `type` field MUST use one of the canonical English values from the schema; do not translate these enum values even when the project language is Portuguese. Return a non-authoritative proposal for human review.")
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
            unit_type = canonical_unit_type(x.get("type", "capability"))
            items.append(UnitProposal(key,x.get("name","").strip(),x.get("scope","").strip(),x.get("rationale","").strip(),unit_type,parent,deps))
        _validate(items) if data.get("decompose", True) else None
        if data.get("decompose", True) and not items:
            raise ThesysError("OpenAI returned decompose=true without any Engineering Units.")
        if not data.get("decompose", True) and items:
            raise ThesysError("OpenAI returned Engineering Units while decompose=false.")
        return UnitProposalResult(bool(data.get("decompose", True)), tuple(items))


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


def generate_unit_proposal(project, provider="openai", methodology=None):
    # Use the same authoritative gate semantics exposed by `thesys status`.
    # This avoids a second, subtly different approval implementation.
    if methodology is None:
        from .methodology import load_methodology
        methodology = load_methodology(Path(__file__).resolve().parents[2])
    from .gates import status
    if status(project, methodology, "default").get("intent", {}).get("status") != "approved":
        raise ProjectError("Engineering unit proposals require the current Intent to be human-approved first.")
    intent = read_intent(project)
    if proposal_path(project).is_file():
        data,_=read_proposal(project)
        if data.get("status")=="accepted": raise ProjectError("Engineering unit proposal has already been accepted.")
        raise ProjectError("An engineering unit proposal already exists; review or accept it before generating another.")
    agent = MockUnitAgent() if provider=="mock" else OpenAIUnitAgent() if provider=="openai" else None
    if agent is None: raise ThesysError(f"Unknown unit proposal agent: {provider}")
    result = agent.propose_units(intent)
    return write_proposal(project, agent.name, result.units, result.decompose)


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
