"""Domain services for clarification-question identity and normalization."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .errors import ProjectError
from .io import read_text

QUESTION_ID_RE = re.compile(r"^QST-(\d{3})$")


def validate_question_id(question_id: str) -> str:
    """Validate and return a canonical Thesys clarification-question ID."""
    if not QUESTION_ID_RE.fullmatch(question_id):
        raise ProjectError(
            f"Invalid question ID '{question_id}'. "
            "Question IDs are assigned by Thesys and must use the QST-NNN format."
        )
    return question_id


def _proposal_files(project: Path):
    yield from (project / ".thesys" / "proposals").glob("*/*.json")


def _used_question_ids(project: Path) -> set[str]:
    """Collect canonical question IDs already persisted in project state."""
    used: set[str] = set()

    answers_path = project / ".thesys" / "answers.json"
    if answers_path.is_file():
        try:
            answers = json.loads(read_text(answers_path))
        except (OSError, json.JSONDecodeError):
            answers = {}
        used.update(
            question_id
            for question_id in answers
            if QUESTION_ID_RE.fullmatch(str(question_id))
        )

    for path in _proposal_files(project):
        try:
            proposal = json.loads(read_text(path))
        except (OSError, json.JSONDecodeError):
            continue
        for question in proposal.get("questions", []):
            question_id = question.get("id")
            if isinstance(question_id, str) and QUESTION_ID_RE.fullmatch(question_id):
                used.add(question_id)

    return used


def allocate_question_id(project: Path, reserved: set[str] | None = None) -> str:
    """Allocate the next project-wide canonical clarification-question ID."""
    used = _used_question_ids(project)
    used.update(reserved or set())
    numbers = [int(match.group(1)) for question_id in used if (match := QUESTION_ID_RE.fullmatch(question_id))]
    next_number = max(numbers, default=0) + 1
    return f"QST-{next_number:03d}"
