"""Durable human guidance for proposal generation and lifecycle revalidation."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .errors import ProjectError
from .io import read_text, write_text
from .registry import add_event

GUIDANCE_TYPES = {"directive", "review-note", "reference", "attachment"}
TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".json", ".yaml", ".yml", ".csv", ".xml", ".html", ".htm"
}


def _root(project: Path) -> Path:
    return project / ".thesys" / "guidance"


def _files(project: Path):
    yield from sorted(_root(project).glob("GUD-*.json"))


def _load(path: Path) -> dict:
    try:
        return json.loads(read_text(path))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProjectError(f"Invalid guidance record: {path}") from exc


def list_guidance(project: Path) -> list[dict]:
    return [_load(path) for path in _files(project)]


def _allocate_id(project: Path) -> str:
    numbers = []
    for item in list_guidance(project):
        value = str(item.get("id", ""))
        if value.startswith("GUD-"):
            try:
                numbers.append(int(value.split("-")[-1]))
            except ValueError:
                pass
    return f"GUD-{max(numbers, default=0) + 1:03d}"


def _hash_bytes(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _attachment_content(path: Path) -> str:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        raise ProjectError(
            "Guidance attachments must currently be UTF-8 text files "
            f"({', '.join(sorted(TEXT_EXTENSIONS))}); received '{path.suffix or '<no extension>'}'."
        )
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ProjectError(f"Guidance attachment is not valid UTF-8 text: {path}") from exc



def _invalidate_proposals(project: Path, methodology, guidance: dict) -> list[str]:
    """Mark non-authoritative proposals at and after guidance scope for regeneration."""
    source_index = _stage_index(methodology, guidance["stage"])
    invalidated = []
    for path in (project / ".thesys" / "proposals").glob("*/*.json"):
        try:
            proposal = _load(path)
        except ProjectError:
            continue
        stage_id = str(proposal.get("stage", ""))
        stage_index = _stage_index(methodology, stage_id)
        if stage_index < source_index or proposal.get("status") == "accepted":
            continue
        try:
            stage = methodology.stage(stage_id)
        except ProjectError:
            continue
        proposal_unit = proposal.get("unit")
        source_stage = methodology.stage(guidance["stage"])
        if source_stage.config.get("scope") == "project":
            applies = True
        else:
            applies = proposal_unit == guidance.get("unit")
        if not applies:
            continue
        if proposal.get("status") != "needs_regeneration":
            proposal["status"] = "needs_regeneration"
            write_text(path, json.dumps(proposal, ensure_ascii=False, indent=2) + "\n")
            invalidated.append(str(path))
    return invalidated

def add_guidance(
    project: Path,
    stage: str,
    unit: str,
    guidance_type: str,
    content: str,
    title: str = "",
    file: str | None = None,
    methodology=None,
) -> Path:
    guidance_type = guidance_type.strip().lower()
    if guidance_type not in GUIDANCE_TYPES:
        raise ProjectError(f"Invalid guidance type '{guidance_type}'. Expected: {', '.join(sorted(GUIDANCE_TYPES))}.")
    if not content.strip() and not file:
        raise ProjectError("Guidance content cannot be empty.")
    if file and guidance_type not in {"reference", "attachment"}:
        raise ProjectError("--file is only valid for reference or attachment guidance.")

    if methodology is not None:
        stage_def = methodology.stage(stage)
        from .workflow import stage_unit
        unit = stage_unit(project, methodology, stage_def, unit)
        if stage_def.config.get("scope") != "project":
            from .project import scope_info
            scope_info(project, unit)

    guidance_id = _allocate_id(project)
    root = _root(project)
    root.mkdir(parents=True, exist_ok=True)
    record = {
        "schema": "1",
        "id": guidance_id,
        "type": guidance_type,
        "stage": stage,
        "unit": unit,
        "title": title.strip() or guidance_type.replace("-", " ").title(),
        "content": content.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": "human",
        "status": "active",
    }

    if file:
        source = Path(file).expanduser().resolve()
        if not source.is_file():
            raise ProjectError(f"Guidance attachment not found: {source}")
        attachment_dir = root / "attachments"
        attachment_dir.mkdir(parents=True, exist_ok=True)
        destination = attachment_dir / f"{guidance_id}-{source.name}"
        shutil.copy2(source, destination)
        record["attachment"] = {
            "path": str(destination.relative_to(project)).replace("\\", "/"),
            "filename": source.name,
            "sha256": _hash_bytes(destination),
            "content": _attachment_content(source),
        }

    path = root / f"{guidance_id}.json"
    write_text(path, json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    invalidated = _invalidate_proposals(project, methodology, record) if methodology is not None else []
    add_event(
        project,
        "human-guidance-added",
        guidance_id,
        {"stage": stage, "unit": unit, "type": guidance_type, "invalidated_proposals": len(invalidated)},
    )
    return path


def _stage_index(methodology, stage_id: str) -> int:
    return next((index for index, stage in enumerate(methodology.stages) if stage.id == stage_id), -1)


def applicable_guidance(project: Path, methodology, stage, unit) -> list[dict]:
    """Return active guidance that is in scope for this stage and target.

    Guidance is forward-propagating: an instruction attached to an upstream
    stage remains an input to every later stage in the same lifecycle branch.
    Project-scoped guidance applies to all downstream unit and project stages;
    unit-scoped guidance applies only to that unit and its downstream stages.
    """
    current_index = _stage_index(methodology, stage.id)
    from .workflow import stage_unit
    current_unit = stage_unit(project, methodology, stage, unit)
    result = []
    for item in list_guidance(project):
        if item.get("status") != "active":
            continue
        item_index = _stage_index(methodology, str(item.get("stage", "")))
        if item_index < 0 or item_index > current_index:
            continue
        source_stage = methodology.stage(item["stage"])
        source_unit = item.get("unit")
        if stage.config.get("scope") == "project":
            # Project/aggregate stages consume all applicable child-unit guidance
            # as well as project-scoped guidance. This preserves propagation
            # across the unit-to-system integration boundary.
            result.append(item)
        elif source_stage.config.get("scope") == "project":
            result.append(item)
        elif source_unit == current_unit:
            result.append(item)
    return sorted(result, key=lambda item: (item.get("created_at", ""), item.get("id", "")))


def guidance_inputs(project: Path, methodology, stage, unit) -> dict:
    result = {}
    for item in applicable_guidance(project, methodology, stage, unit):
        result[item["id"]] = {
            "type": item.get("type"),
            "stage": item.get("stage"),
            "unit": item.get("unit"),
            "title": item.get("title"),
            "content": item.get("content", ""),
            "attachment": item.get("attachment"),
        }
    return result


def guidance_fingerprint(project: Path, methodology, stage, unit) -> str:
    payload = guidance_inputs(project, methodology, stage, unit)
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
