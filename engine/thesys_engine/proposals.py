import json
from .errors import ProjectError
from .io import read_text
from .agents import get_agent,GenerationContext
from .workflow import can_propose,save_proposal,load_proposal,accept_proposal,proposal_questions,authoritative_inputs,_load_answers,proposal_path
from .project import unit_info,project_language

def _context(project,m,unit):
 st=authoritative_inputs(project,m,m.stage('requirements'),unit)
 # Include every currently authoritative artifact upstream of the requested stage.
 approved={}
 from .workflow import stage_unit
 from .gates import status
 statuses=status(project,m,unit)
 for s in m.stages:
  su=stage_unit(m,s,unit); p=m.artifact_path(project,s,su)
  if p and p.is_file() and statuses.get(s.id,{}).get('status') in {'approved','completed'}: approved[s.id]=read_text(p)
 return GenerationContext(approved.get('intent',''),unit,unit_info(project,unit)['scope'],project_language(project,m.language),approved,_load_answers(project))

def generate(project,m,stage_id,unit,provider='openai'):
 stage=m.stage(stage_id); can_propose(project,m,stage,unit)
 agent=get_agent(provider); c=_context(project,m,unit); result=agent.propose_document(m,stage_id,c)
 return save_proposal(project,stage_id,unit,agent.name,result['content'],result.get('questions',[]),authoritative_inputs(project,m,stage,unit))

def list_proposals(project): return sorted((project/'.thesys/proposals').glob('*/*.json'))
def accept(project,m,stage,unit): return accept_proposal(project,m,stage,unit)
