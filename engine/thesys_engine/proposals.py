import json
from .errors import ProjectError
from .io import read_text
from .agents import get_agent,GenerationContext
from .workflow import can_propose,save_proposal,load_proposal,accept_proposal,proposal_questions,authoritative_inputs,_load_answers,proposal_path
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
            arch=next(m.stage(dep) for dep in stage.depends_on if m.stage(dep).config.get('scope') != 'project')
            p=m.artifact_path(project,arch,key)
            if p and p.is_file() and unit_status.get('architecture',{}).get('status') in {'approved','completed'}:
                approved[f'architecture:{key}']=read_text(p)
                related_units[key]={"name": item.get("name", key), "parent": item.get("parent", "default"), "dependencies": item.get("dependencies", []), "architecture": approved[f'architecture:{key}']}
        scope=unit_info(project,'default')['scope']
        return GenerationContext(approved.get('intent',''), 'default', scope, project_language(project,m.language), approved, _load_answers(project), related_units)
    statuses=status(project,m,unit)
    for s in m.stages:
        su=stage_unit(m,s,unit); p=m.artifact_path(project,s,su)
        if p and p.is_file() and statuses.get(s.id,{}).get('status') in {'approved','completed'}:
            approved[s.id]=read_text(p)
    return GenerationContext(approved.get('intent',''),unit,unit_info(project,unit)['scope'],project_language(project,m.language),approved,_load_answers(project),{})

def generate(project,m,stage_id,unit,provider='openai'):
 stage=m.stage(stage_id); can_propose(project,m,stage,unit)
 agent=get_agent(provider); c=_context(project,m,unit,stage); result=agent.propose_document(m,stage_id,c)
 return save_proposal(project,stage_id,unit,agent.name,result['content'],result.get('questions',[]),authoritative_inputs(project,m,stage,unit),m)

def list_proposals(project): return sorted((project/'.thesys/proposals').glob('*/*.json'))
def accept(project,m,stage,unit): return accept_proposal(project,m,stage,unit)
