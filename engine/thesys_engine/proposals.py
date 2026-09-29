import json
from .errors import ProjectError
from .io import read_text
from .agents import get_agent,GenerationContext
from .workflow import can_propose,save_proposal,load_proposal,accept_proposal,proposal_questions,authoritative_inputs,_load_answers,_clarification_history_for,proposal_path
from .project import unit_info,project_language

def _context(project,m,unit,stage):
    approved={}
    from .workflow import stage_unit
    from .gates import status
    aggregate_stage = stage.config.get('aggregate_units') and stage.config.get('scope') == 'project' and unit == 'default'
    if aggregate_stage:
        project_status=status(project,m,'default')
        for s in m.stages:
            if s.config.get('scope') == 'project':
                p=m.artifact_path(project,s,'default')
                if p and p.is_file() and project_status.get(s.id,{}).get('status') in {'approved','completed'}:
                    approved[s.id]=read_text(p)

        from .project import work_units
        related_units={}
        for item in work_units(project):
            key=item['key']
            unit_status=status(project,m,key)
            unit_inputs={}
            for dep_id in stage.depends_on:
                dep_stage=m.stage(dep_id)
                if dep_stage.config.get('scope') == 'project':
                    continue
                p=m.artifact_path(project,dep_stage,key)
                if p and p.is_file() and unit_status.get(dep_id,{}).get('status') in {'approved','completed'}:
                    content=read_text(p)
                    approved[f'{dep_id}:{key}']=content
                    unit_inputs[dep_id]=content
            related_units[key]={
                "name": item.get("name", key),
                "parent": item.get("parent", "default"),
                "dependencies": item.get("dependencies", []),
                "artifacts": unit_inputs,
            }
            if 'architecture' in unit_inputs:
                related_units[key]['architecture']=unit_inputs['architecture']
        scope=unit_info(project,'default')['scope']
        return GenerationContext(approved.get('intent',''), 'default', scope, project_language(project,m.language), approved, _load_answers(project), related_units, 'system', None, (), _clarification_history_for(project, stage.id, 'default'))

    statuses=status(project,m,unit)
    for s in m.stages:
        su=stage_unit(m,s,unit); p=m.artifact_path(project,s,su)
        if p and p.is_file() and statuses.get(s.id,{}).get('status') in {'approved','completed'}:
            approved[s.id]=read_text(p)
    info = unit_info(project, unit)
    return GenerationContext(
        approved.get('intent',''),
        unit,
        info['scope'],
        project_language(project,m.language),
        approved,
        _load_answers(project),
        {},
        info.get('type', 'system'),
        info.get('parent'),
        tuple(info.get('dependencies', [])),
        _clarification_history_for(project, stage.id, unit),
    )

def _validate_artifact_refs(project, methodology, content):
    """Reject invented artifact references instead of silently rewriting them."""
    import re
    from .registry import get
    known = set(get(project).get("artifacts", {}).keys())
    prefixes = {str(stage.config.get("artifact_prefix", "")).upper() for stage in methodology.stages}
    prefixes.discard("")
    pattern = re.compile(r"\[([A-Z]{2,5}-\d{3})\]")
    unknown = sorted({m.group(1) for m in pattern.finditer(content)
                      if m.group(1).split("-")[0] in prefixes and m.group(1) not in known})
    if unknown:
        raise ProjectError("Generated content contains references to artifacts that do not exist: " + ", ".join(unknown))
    return content


def _context_boundary_section(c):
    pt = c.language.lower().startswith("pt-")
    parent = c.unit_parent or ("não aplicável" if pt else "not applicable")
    if pt:
        return (
            f"- Sistema: a Unidade pertence ao sistema definido pela Intenção aprovada.\n"
            f"- Unidade pai: {parent}.\n"
            f"- Tipo de unidade: {c.unit_type}.\n"
            f"- Escopo da Unidade: {c.unit_scope}."
        )
    return (
        f"- System: the Unit belongs to the system defined by the approved Intent.\n"
        f"- Parent unit: {parent}.\n"
        f"- Unit type: {c.unit_type}.\n"
        f"- Unit scope: {c.unit_scope}."
    )


def _validate_generated_content(content, language, forbidden_placeholders=()):
    """Validate generated prose; never rewrite it."""
    import re
    if not content.strip():
        raise ProjectError("Generated artifact content is empty.")
    if "\ufeff" in content or "\u200b" in content:
        raise ProjectError("Generated artifact contains forbidden zero-width characters.")
    if re.search(r"(?im)^\s*#{2,6}\s+(?:open questions|questões em aberto|questions)\s*$", content):
        raise ProjectError("Generated artifact must not contain a questions section; questions belong to proposal metadata and documentation side panel.")
    if re.search(r"\bQST-\d{3}\b", content, flags=re.IGNORECASE):
        raise ProjectError("Generated artifact must not contain clarification question IDs; questions belong to proposal metadata and documentation side panel.")
    unresolved = sorted({token for token in forbidden_placeholders if token and token in content})
    if unresolved:
        raise ProjectError("Generated artifact contains unresolved template placeholders: " + ", ".join(unresolved))
    if re.search(r"\[(?:Requirement title|Quality attribute|Security requirement|Título do requisito|Atributo de qualidade|Requisito de segurança|Story|Behavior|Criterion|Rule|Task title|Test|Component|Finding|Workstream|Decision)\]", content, flags=re.IGNORECASE):
        raise ProjectError("Generated artifact contains an unresolved placeholder; regenerate the proposal.")
    if language.lower().startswith("pt-"):
        if re.search(r"\b(?:shall|must|should)\b", content, flags=re.IGNORECASE):
            raise ProjectError("Generated pt-BR content contains English normative terminology; regenerate the proposal.")
        if re.search(r"(?m)^\s*(?:Describe|Define|Record|Identify|Explain)\b", content, flags=re.IGNORECASE):
            raise ProjectError("Generated pt-BR content contains template instructions; regenerate the proposal.")
    return content

def _template_placeholders(methodology, stage_id):
    """Return exact placeholder tokens present in the canonical template."""
    from .templates import load_template
    import re
    return tuple(sorted(set(re.findall(r"\[[^]\n]+\]", load_template(methodology, stage_id)))))


def generate(project, m, stage_id, unit, provider='openai'):
    stage = m.stage(stage_id)
    can_propose(project, m, stage, unit)
    agent = get_agent(provider)
    c = _context(project, m, unit, stage)
    result = agent.propose_document(m, stage_id, c)
    sections = dict(result.get('sections') or {})
    if stage_id == 'context':
        sections['system-and-unit-boundary'] = _context_boundary_section(c)
    from .templates import render_template
    content = render_template(m, stage_id, sections, c.language, c.unit)
    content = _validate_generated_content(content, c.language, _template_placeholders(m, stage_id))
    content = _validate_artifact_refs(project, m, content)
    questions = [
        {
            **q,
            'question': str(q.get('question', '')).strip(),
            'why': str(q.get('why', '')).strip(),
        }
        for q in result.get('questions', [])
    ]
    if stage_id == 'context' and c.unit != 'default' and c.unit_parent:
        questions = [
            q for q in questions
            if 'unidade pai' not in q.get('question', '').lower()
            and 'parent unit' not in q.get('question', '').lower()
        ]
    return save_proposal(
        project, stage_id, unit, agent.name, content,
        questions, authoritative_inputs(project, m, stage, unit), m,
    )

def list_proposals(project): return sorted((project/'.thesys/proposals').glob('*/*.json'))
def accept(project,m,stage,unit): return accept_proposal(project,m,stage,unit)
