from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
import re
import unicodedata

from .errors import ProjectError, ThesysError
from .io import read_text, write_text
from .intents import intent_digest, read_intent
from .project import create_unit, project_key
from .workflow import proposal_path as lifecycle_proposal_path, sha


ENGINEERING_UNITS_STAGE = "engineering-units"


@dataclass(frozen=True)
class UnitProposal:
    key: str
    name: str
    scope: str
    rationale: str
    unit_type: str = "capability"
    parent: str = "project"
    dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class UnitProposalResult:
    decompose: bool
    units: tuple[UnitProposal, ...] = ()


def proposal_dir(project):
    """Canonical lifecycle proposal location for the Engineering Units stage."""
    return lifecycle_proposal_path(project, ENGINEERING_UNITS_STAGE, project_key(project)) .parent


def proposal_path(project):
    return lifecycle_proposal_path(project, ENGINEERING_UNITS_STAGE, project_key(project))


def _legacy_proposal_path(project):
    return project / ".thesys" / "proposals" / "engineering-units" / "proposal.json"


def _readable_proposal_path(project):
    current = proposal_path(project)
    if current.is_file():
        return current
    legacy = _legacy_proposal_path(project)
    return legacy if legacy.is_file() else current


def slug(value):
    value = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return value[:64]


ALLOWED_UNIT_TYPES = (
    "system", "domain", "capability", "epic", "module", "service", "feature",
    "change", "defect", "migration", "security-remediation",
    "architecture-initiative", "technical-debt", "platform-change",
)

_UNIT_TYPE_ALIASES = {
    "sistema": "system", "dominio": "domain", "capacidade": "capability", "epico": "epic",
    "modulo": "module", "servico": "service", "funcionalidade": "feature", "mudanca": "change",
    "defeito": "defect", "migracao": "migration", "remediacao-de-seguranca": "security-remediation",
    "iniciativa-de-arquitetura": "architecture-initiative", "divida-tecnica": "technical-debt",
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
        if item.unit_type not in ALLOWED_UNIT_TYPES:
            raise ThesysError(f"Unsupported engineering unit type: {item.unit_type}")

    parents = {item.key: item.parent for item in items if item.parent in keys}
    for key in parents:
        seen = set(); current = key
        while current in parents:
            if current in seen:
                raise ThesysError(f"Engineering unit parent hierarchy contains a cycle at: {current}")
            seen.add(current); current = parents[current]

    dependencies = {item.key: set(item.dependencies) & keys for item in items}
    colors = {key: 0 for key in dependencies}
    def visit(key):
        if colors[key] == 1:
            raise ThesysError(f"Engineering unit dependency graph contains a cycle at: {key}")
        if colors[key] == 2:
            return
        colors[key] = 1
        for dependency in dependencies[key]:
            visit(dependency)
        colors[key] = 2
    for key in dependencies:
        visit(key)


def _input_fingerprint(project, methodology):
    from .workflow import authoritative_inputs
    from .guidance import guidance_inputs
    stage = methodology.stage(ENGINEERING_UNITS_STAGE)
    inputs = {
        "authoritative": authoritative_inputs(project, methodology, stage, project_key(project)),
        "guidance": guidance_inputs(project, methodology, stage, project_key(project)),
    }
    return sha(json.dumps(inputs, ensure_ascii=False, sort_keys=True))


def write_proposal(project, provider, items, decompose=True, input_fingerprint=None):
    if decompose:
        _validate(items)
    elif items:
        raise ThesysError("Engineering unit proposal contains units while decomposition is disabled.")
    path = proposal_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    proposal_id = "PROP-" + sha(json.dumps({"input_fingerprint": input_fingerprint, "provider": provider, "units": [x.key for x in items]}, sort_keys=True))[:12].upper()
    payload = {
        "schema": "2",
        "proposal_id": proposal_id,
        "stage": ENGINEERING_UNITS_STAGE,
        "unit": project_key(project),
        "status": "proposed",
        "provider": provider,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_intent": "engineering/intent/intent.md",
        "intent_sha256": intent_digest(project),
        "input_fingerprint": input_fingerprint,
        "decompose": bool(decompose),
        "engineering_units": [
            {"key": x.key, "name": x.name, "scope": x.scope, "rationale": x.rationale,
             "type": x.unit_type, "parent": x.parent, "dependencies": list(x.dependencies)}
            for x in items
        ],
    }
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return path


def read_proposal(project):
    path = _readable_proposal_path(project)
    if not path.is_file():
        raise ProjectError("Engineering unit proposal not found. Generate the Engineering Units stage first.")
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise ProjectError("Engineering unit proposal is invalid JSON.") from exc
    root = project_key(project)
    items = []
    for x in data.get("engineering_units", []):
        parent = x.get("parent", root)
        if parent in {"default", "project"}:
            parent = root
        items.append(UnitProposal(
            key=x.get("key", ""), name=x.get("name", ""), scope=x.get("scope", ""),
            rationale=x.get("rationale", ""), unit_type=canonical_unit_type(x.get("type", "capability")),
            parent=parent, dependencies=tuple(x.get("dependencies", []))
        ))
    if data.get("decompose", bool(items)):
        _validate(items)
    elif items:
        raise ProjectError("Engineering unit proposal is inconsistent: units exist while decomposition is disabled.")
    return data, items


def _capability_lines(intent):
    lines = intent.splitlines(); in_section = False; values = []
    headings = ("capabilities", "expected capabilities", "in scope", "scope")
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            in_section = stripped[3:].strip().lower() in headings
            continue
        if not in_section:
            continue
        if re.match(r"^(?:[-*]|\d+\.)\s+", stripped):
            value = re.sub(r"^(?:[-*]|\d+\.)\s+", "", stripped).strip()
            if value and not value.startswith("["):
                values.append(value.rstrip("."))
    return values


class MockUnitAgent:
    name = "mock"
    def propose_units(self, intent, governance="", project_root="project"):
        items = []
        seen = set()
        for value in _capability_lines(intent):
            key = slug(value)
            if not key or key in seen:
                continue
            seen.add(key)
            items.append(UnitProposal(key, value, value + ".", "The capability is explicitly stated in the Intent.", parent=project_root))
        return UnitProposalResult(bool(items), tuple(items))


class OpenAIUnitAgent:
    name = "openai"
    def __init__(self, client=None):
        if client is not None:
            self.client = client
        else:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise ThesysError("The OpenAI SDK is not installed. Reinstall Thesys with: python -m pip install -e .") from exc
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                raise ThesysError("OPENAI_API_KEY is not configured.")
            self.client = OpenAI(api_key=key)
        self.model = os.getenv("THESYS_OPENAI_MODEL", "gpt-5.6-luna")

    def propose_units(self, intent, governance="", project_root="project"):
        schema = {
            "type": "object",
            "properties": {
                "decompose": {"type": "boolean"},
                "engineering_units": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"}, "name": {"type": "string"},
                        "scope": {"type": "string"}, "rationale": {"type": "string"},
                        "type": {"type": "string", "enum": list(ALLOWED_UNIT_TYPES)},
                        "parent": {"type": "string"}, "dependencies": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["key", "name", "scope", "rationale", "type", "parent", "dependencies"],
                    "additionalProperties": False,
                }},
            },
            "required": ["decompose", "engineering_units"], "additionalProperties": False,
        }
        instructions = (
            "Propose Engineering Units for the current lifecycle stage from the authoritative Intent and Governance. "
            "First decide whether decomposition is justified by the complexity and scope explicitly established by those artifacts. "
            "If the project is small enough to remain coherent as one system, set decompose=false and return an empty engineering_units array. "
            "If decomposition is justified, propose only a small number of coherent units. Units are organizational scopes used to organize engineering work; "
            "they are not lifecycle stages and do not automatically define runtime components, deployment boundaries, APIs or architecture boundaries. "
            "Do not invent requirements, technologies, APIs, architecture or business decisions. The type field MUST use canonical English enum values. "
            "The parent of every top-level Engineering Unit MUST be the Project root key supplied by the runtime; never invent a synthetic root Engineering Unit. Return a non-authoritative proposal for human review."
        )
        input_text = "Authoritative Intent:\n\n" + intent + "\n\nAuthoritative Governance:\n\n" + governance
        try:
            response = self.client.responses.create(
                model=self.model, instructions=instructions, input=input_text,
                text={"format": {"type": "json_schema", "name": "thesys_engineering_unit_proposal", "strict": True, "schema": schema}},
            )
        except Exception as exc:
            raise ThesysError(f"OpenAI request failed: {exc}") from exc
        try:
            data = json.loads(response.output_text)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ThesysError("OpenAI returned an invalid engineering unit proposal.") from exc
        items = []
        for x in data.get("engineering_units", []):
            key = slug(x.get("key", "")); parent = slug(x.get("parent", project_root)) or project_root
            deps = tuple(slug(v) for v in x.get("dependencies", []))
            unit_type = canonical_unit_type(x.get("type", "capability"))
            items.append(UnitProposal(key, x.get("name", "").strip(), x.get("scope", "").strip(), x.get("rationale", "").strip(), unit_type, parent, deps))
        if data.get("decompose", True):
            _validate(items)
            if not items:
                raise ThesysError("OpenAI returned decompose=true without any Engineering Units.")
        elif items:
            raise ThesysError("OpenAI returned Engineering Units while decompose=false.")
        return UnitProposalResult(bool(data.get("decompose", True)), tuple(items))


def _authoritative_inputs(project, methodology):
    from .workflow import authoritative_inputs
    stage = methodology.stage(ENGINEERING_UNITS_STAGE)
    return authoritative_inputs(project, methodology, stage, project_key(project))


def generate_unit_proposal(project, provider="openai", methodology=None):
    if methodology is None:
        from .methodology import load_methodology
        methodology = load_methodology(Path(__file__).resolve().parents[2])
    from .gates import status
    if status(project, methodology, project_key(project)).get("governance", {}).get("status") != "approved":
        raise ProjectError("Engineering unit proposals require current Governance approval first.")
    intent = read_intent(project)
    governance_path = methodology.artifact_path(project, methodology.stage("governance"), project_key(project))
    governance = read_text(governance_path) if governance_path and governance_path.is_file() else ""
    path = proposal_path(project)
    if path.is_file():
        data, _ = read_proposal(project)
        status = data.get("status")
        if status == "accepted":
            raise ProjectError("Engineering unit proposal has already been accepted.")
        if status != "needs_regeneration":
            raise ProjectError("An Engineering Units proposal already exists; review or accept it before generating another.")
        # A stale/non-authoritative proposal is explicitly eligible for regeneration.
        # The new proposal replaces the current working copy while the registry/event
        # history preserves the fact that the previous proposal existed.
    agent = MockUnitAgent() if provider == "mock" else OpenAIUnitAgent() if provider == "openai" else None
    if agent is None:
        raise ThesysError(f"Unknown unit proposal agent: {provider}")
    result = agent.propose_units(intent, governance, project_key(project))
    return write_proposal(project, agent.name, result.units, result.decompose, _input_fingerprint(project, methodology))


def render_authoritative_artifact(project, methodology, data, items):
    language = __import__("thesys_engine.project", fromlist=["project_language"]).project_language(project, methodology.language)
    name = __import__("thesys_engine.project", fromlist=["project_info"]).project_info(project).get("name", project.name)
    pt = language.lower().startswith("pt-")
    yes, no = ("Sim", "Não") if pt else ("Yes", "No")
    lines = [
        f"# {'Unidades de Engenharia' if pt else 'Engineering Units'} — {name}",
        "", f"## {'Decisão de decomposição' if pt else 'Decomposition decision'}", "",
        f"- {'Decomposição' if pt else 'Decomposition'}: {yes if data.get('decompose') else no}",
        f"- {'Provedor da proposta' if pt else 'Proposal provider'}: {data.get('provider', 'unknown')}",
        "",
        f"## {'Mapa das Unidades de Engenharia' if pt else 'Engineering Unit map'}", "",
        f"| {'Unidade' if pt else 'Unit'} | {'Nome' if pt else 'Name'} | {'Tipo' if pt else 'Type'} | {'Pai' if pt else 'Parent'} | {'Escopo' if pt else 'Scope'} | {'Dependências' if pt else 'Dependencies'} |",
        "|---|---|---|---|---|---|",
    ]
    if items:
        for item in items:
            deps = ", ".join(item.dependencies) or "—"
            lines.append(f"| `{item.key}` | {item.name} | `{item.unit_type}` | `{item.parent}` | {item.scope} | {deps} |")
    else:
        lines.append(f"| `{project_key(project)}` | {name} | `project` | — | {'Projeto completo' if pt else 'Project-wide'} | — |")
    lines += [
        "", f"## {'Limite de complexidade' if pt else 'Complexity boundary'}", "",
        ("As Unidades de Engenharia são escopos organizacionais para o trabalho do ciclo de vida. Elas não definem automaticamente componentes de execução, APIs, implantação ou limites arquiteturais."
         if pt else
         "Engineering Units are organizational scopes for lifecycle work. They do not automatically define runtime components, APIs, deployment boundaries or architecture boundaries."),
        "",
        f"## {'Governança' if pt else 'Governance'}", "",
        ("A decomposição acima foi derivada de uma proposta não autoritativa e só se torna parte da estrutura do projeto após aprovação humana desta etapa."
         if pt else
         "The decomposition above was derived from a non-authoritative proposal and becomes part of the project structure only after human approval of this stage."),
    ]
    return "\n".join(lines) + "\n"


def accept_unit_proposal(project, methodology):
    data, items = read_proposal(project)
    if data.get("status") != "proposed":
        raise ProjectError("Only a proposed Engineering Units proposal can be accepted.")
    current = _input_fingerprint(project, methodology)
    if data.get("input_fingerprint") and data.get("input_fingerprint") != current:
        raise ProjectError("Engineering Units proposal is stale because an authoritative upstream artifact changed. Generate a new proposal.")
    if data.get("intent_sha256") != intent_digest(project):
        raise ProjectError("Engineering Units proposal is stale because the authoritative Intent changed. Generate a new proposal.")
    existing = {p.stem for p in (project / ".thesys" / "units").glob("*.json")}
    for item in items:
        if item.key in existing:
            raise ProjectError(f"Engineering unit already exists: {item.key}")
    keys = {x.key for x in items}
    for item in items:
        if item.parent not in {project_key(project)} and item.parent not in keys and item.parent not in existing:
            raise ProjectError(f"Engineering unit '{item.key}' references unknown parent: {item.parent}")
        unknown = [d for d in item.dependencies if d not in keys and d not in existing]
        if unknown:
            raise ProjectError(f"Engineering unit '{item.key}' references unknown dependencies: {', '.join(unknown)}")
    created = []; remaining = list(items)
    try:
        while remaining:
            progressed = False
            for item in remaining[:]:
                if item.parent != project_key(project) and item.parent in keys and item.parent not in existing:
                    if item.parent not in {x.key for x in remaining}:
                        continue
                    continue
                path = create_unit(project, item.key, item.name, item.scope, item.unit_type, item.parent, methodology, dependencies=list(item.dependencies))
                created.append(path); existing.add(item.key); remaining.remove(item); progressed = True
            if not progressed:
                raise ProjectError("Engineering unit proposal contains an unresolved parent hierarchy.")
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    # The generic lifecycle approval path owns the authoritative approval record
    # and proposal status. This function only materializes the accepted unit map.
    artifact = methodology.artifact_path(project, methodology.stage(ENGINEERING_UNITS_STAGE), project_key(project))
    artifact.parent.mkdir(parents=True, exist_ok=True)
    write_text(artifact, render_authoritative_artifact(project, methodology, data, items))
    return artifact
