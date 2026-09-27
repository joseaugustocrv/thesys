from pathlib import Path
import json

from .io import read_text
from .registry import get
from .project import project_info
from .project_templates import load_project_templates


def validate(project,m):
    findings=[]
    if not m.definition.is_file(): findings.append("Methodology definition is missing.")
    if not (m.root/"methodology/definition/catalog.json").is_file(): findings.append("Methodology capability catalog is missing.")
    try:
        templates=load_project_templates(m.root)
    except Exception as exc:
        templates={}; findings.append(f"Project template catalog is invalid: {exc}")
    for s in m.stages:
        if s.template and not (m.root/s.template).is_file(): findings.append(f"Missing template for stage '{s.id}': {s.template}")
        if s.artifact and "{unit}" in s.artifact and "unit" not in s.artifact: findings.append(f"Invalid unit artifact path for '{s.id}'.")
    ids={s.id for s in m.stages}
    for s in m.stages:
        if s.id in s.depends_on: findings.append(f"Stage '{s.id}' cannot depend on itself.")
        if any(d not in ids for d in s.depends_on): findings.append(f"Stage '{s.id}' has an unknown dependency.")
    catalog=m.catalog
    if not catalog.get("artifact_types"): findings.append("Capability catalog has no artifact types.")
    if not catalog.get("workflows"): findings.append("Capability catalog has no specialized workflows.")

    project_file=project/".thesys"/"project.yaml"
    if not project_file.is_file():
        findings.append("Project metadata is missing: .thesys/project.yaml")
    else:
        info=project_info(project)
        template_id=info.get("template")
        if not template_id: findings.append("Project metadata has no template.")
        elif template_id not in templates: findings.append(f"Project references unknown template: {template_id}")
        if not info.get("key"): findings.append("Project metadata has no key.")
        if not info.get("name"): findings.append("Project metadata has no name.")
        if not info.get("id"): findings.append("Project metadata has no stable project ID.")

    registry=get(project)
    for aid,item in registry.get("artifacts",{}).items():
        if not item.get("path"): findings.append(f"Artifact '{aid}' has no path.")
        raw=item.get("path")
        if raw:
            try:
                Path(raw).resolve().relative_to(project.resolve())
            except ValueError:
                findings.append(f"Artifact '{aid}' points outside the project: {raw}")
    return findings
