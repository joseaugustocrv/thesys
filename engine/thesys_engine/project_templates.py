from dataclasses import dataclass
import json
from pathlib import Path

from .errors import MethodologyError
from .io import read_text


@dataclass(frozen=True)
class ProjectTemplate:
    id: str
    name: str
    description: str
    kind: str
    root_unit_type: str
    root_scope: str
    agent_provider: str
    directories: tuple[str, ...]


def load_project_templates(methodology_root: Path) -> dict[str, ProjectTemplate]:
    path = methodology_root / "methodology" / "project-templates" / "catalog.json"
    if not path.is_file():
        raise MethodologyError(f"Project template catalog not found: {path}")
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise MethodologyError("Project template catalog is invalid JSON.") from exc

    raw_templates = data.get("templates")
    if not isinstance(raw_templates, dict) or not raw_templates:
        raise MethodologyError("Project template catalog must define at least one template.")

    result: dict[str, ProjectTemplate] = {}
    for template_id, raw in raw_templates.items():
        if not isinstance(raw, dict):
            raise MethodologyError(f"Project template '{template_id}' must be a mapping.")
        template = ProjectTemplate(
            id=str(template_id),
            name=str(raw.get("name", template_id)),
            description=str(raw.get("description", "")),
            kind=str(raw.get("kind", "software-system")),
            root_unit_type=str(raw.get("root_unit_type", "system")),
            root_scope=str(raw.get("root_scope", "system root")),
            agent_provider=str(raw.get("agent_provider", "openai")),
            directories=tuple(str(x) for x in (raw.get("directories", []) or [])),
        )
        if not template.name.strip():
            raise MethodologyError(f"Project template '{template_id}' has no name.")
        if not template.root_unit_type.strip():
            raise MethodologyError(f"Project template '{template_id}' has no root unit type.")
        result[template.id] = template
    default_id = str(data.get("default", ""))
    if default_id not in result:
        raise MethodologyError(f"Project template default '{default_id}' is not defined.")
    return result


def get_project_template(methodology_root: Path, template_id: str | None = None) -> ProjectTemplate:
    templates = load_project_templates(methodology_root)
    if template_id is None:
        catalog_path = methodology_root / "methodology" / "project-templates" / "catalog.json"
        data = json.loads(read_text(catalog_path))
        template_id = str(data["default"])
    try:
        return templates[template_id]
    except KeyError as exc:
        available = ", ".join(sorted(templates))
        raise MethodologyError(
            f"Unknown project template '{template_id}'. Available templates: {available}."
        ) from exc
