"""Structured lifecycle-template contracts and deterministic rendering.

Templates define the document structure. Agents provide section content only.
The renderer owns headings, titles, placeholders and language-specific labels.
No generated prose is rewritten after the agent response.
"""
from dataclasses import dataclass
from pathlib import Path
import json
import re

from .io import read_text

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")

@dataclass(frozen=True)
class TemplateSection:
    id: str
    level: int
    heading: str
    parent: str | None = None

@dataclass(frozen=True)
class TemplateContract:
    stage: str
    title: str
    sections: tuple[TemplateSection, ...]
    source: Path

    @property
    def section_ids(self):
        return tuple(s.id for s in self.sections)


def _slug(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "section"


def load_contract(methodology, stage_id: str) -> TemplateContract:
    stage = methodology.stage(stage_id)
    if not stage.template:
        raise ValueError(f"Stage '{stage_id}' has no template.")
    path = methodology.root / stage.template
    text = read_text(path)
    headings = []
    stack = []
    for line in text.splitlines():
        match = _HEADING.match(line)
        if not match:
            continue
        level = len(match.group(1))
        heading = match.group(2).strip()
        while stack and stack[-1][0] >= level:
            stack.pop()
        parent = stack[-1][1] if stack else None
        section_id = _slug(heading)
        if level == 1:
            title = heading
        else:
            headings.append(TemplateSection(section_id, level, heading, parent))
            stack.append((level, section_id))
    if not headings:
        raise ValueError(f"Template '{path}' must define at least one section.")
    return TemplateContract(stage_id, title, tuple(headings), path)


def load_localization(methodology, language: str) -> dict:
    path = methodology.root / "methodology" / "localization" / f"{language}.json"
    if not path.is_file():
        path = methodology.root / "methodology" / "localization" / "en-US.json"
    if not path.is_file():
        return {}
    return json.loads(read_text(path))


def section_labels(contract: TemplateContract, localization: dict) -> dict:
    labels = localization.get("headings", {})
    return {s.id: labels.get(s.heading, s.heading) for s in contract.sections}


def _render_title(title: str, localization: dict, unit_key: str) -> str:
    titles = localization.get("titles", {})
    localized = titles.get(title, title)
    return localized.replace("[Unit key]", unit_key)


def render_sections(contract: TemplateContract, sections: dict, localization: dict, unit_key: str = "project") -> str:
    labels = section_labels(contract, localization)
    lines = [f"# {_render_title(contract.title, localization, unit_key)}", ""]
    for section in contract.sections:
        heading = labels[section.id]
        level = section.level
        lines.append(f"{'#' * level} {heading}")
        content = sections.get(section.id, "")
        if content is None:
            content = ""
        content = str(content).strip()
        if content:
            lines.extend(["", content])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def contract_schema(contract: TemplateContract) -> dict:
    properties = {s.id: {"type": "string"} for s in contract.sections}
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }
