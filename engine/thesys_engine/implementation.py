import json
from pathlib import Path
from .errors import ProjectError
from .io import read_text,write_text
from .workflow import can_propose,save_proposal,load_proposal,proposal_questions,authoritative_inputs,_load_answers,_clarification_history_for,proposal_path
from .guidance import guidance_inputs
from .agents import get_agent,GenerationContext
from .project import scope_info,project_language,project_key
from .gates import status

def _context(project,m,unit):
 from .workflow import stage_unit
 approved={}; st=status(project,m,unit)
 for s in m.stages:
  p=m.artifact_path(project,s,stage_unit(project,m,s,unit))
  if p and p.is_file() and st.get(s.id,{}).get('status') in {'approved','completed'}: approved[s.id]=read_text(p)
 return GenerationContext(approved.get('intent',''),unit,scope_info(project,unit)['scope'],project_language(project,m.language),approved,_load_answers(project),{},scope_info(project,unit).get('type','system'),scope_info(project,unit).get('parent'),tuple(scope_info(project,unit).get('dependencies',[])),_clarification_history_for(project,'implementation',unit),{},guidance_inputs(project,m, m.stage('implementation'), unit))

def propose(project,m,unit=None,provider='openai'):
 unit = unit or project_key(project)
 stage=m.stage('implementation'); can_propose(project,m,stage,unit)
 c=_context(project,m,unit); result=get_agent(provider).propose_code(m,c)
 inputs={'authoritative':authoritative_inputs(project,m,stage,unit),'guidance':guidance_inputs(project,m,stage,unit)}
 content=json.dumps({'files':result.get('files',{})},ensure_ascii=False,indent=2)
 return save_proposal(project,'implementation',unit,provider,content,result.get('questions',[]),inputs,m)

def read_impl_proposal(project,m,unit=None):
 unit = unit or project_key(project)
 p=proposal_path(project,'implementation',unit,m)
 if not p.is_file(): raise ProjectError('Implementation proposal not found. Run thesys implementation propose first.')
 return json.loads(read_text(p))

def accept(project,m,unit=None):
 unit = unit or project_key(project)
 p=read_impl_proposal(project,m,unit)
 if proposal_questions(project,p): raise ProjectError('Implementation proposal has unanswered blocking questions.')
 stage=m.stage('implementation'); inputs={'authoritative':authoritative_inputs(project,m,stage,unit),'guidance':guidance_inputs(project,m,stage,unit)}
 import hashlib
 if p.get('input_fingerprint')!=hashlib.sha256(json.dumps(inputs,ensure_ascii=False,sort_keys=True).encode()).hexdigest(): raise ProjectError('Implementation proposal is stale; regenerate it.')
 files=json.loads(p['content']).get('files',{})
 if isinstance(files,list):
  normalized={}
  for item in files:
   if not isinstance(item,dict) or not isinstance(item.get('path'),str) or not isinstance(item.get('content'),str):
    raise ProjectError('Invalid implementation proposal: each file must contain string path and content.')
   raw=item['path']
   if raw in normalized:
    raise ProjectError(f'Duplicate generated path: {raw}')
   normalized[raw]=item['content']
  files=normalized
 elif isinstance(files,dict):
  if any(not isinstance(raw,str) or not isinstance(content,str) for raw,content in files.items()):
   raise ProjectError('Invalid implementation proposal: file paths and contents must be strings.')
 else:
  raise ProjectError('Invalid implementation proposal: files must be a list or object.')
 rules=m.rules.get('implementation',{}); allowed=set(rules.get('allowed_roots',[])); allowed_root_files=set(rules.get('allowed_root_files',[]))
 manifest=[]
 for raw,content in files.items():
  rel=Path(raw)
  is_root_file=len(rel.parts)==1 and raw in allowed_root_files
  if rel.is_absolute() or '..' in rel.parts or not rel.parts or (rel.parts[0] not in allowed and not is_root_file): raise ProjectError(f'Unsafe generated path: {raw}')
  target=project/rel; target.parent.mkdir(parents=True,exist_ok=True); write_text(target,content); manifest.append(raw)
 ex=m.execution_path(project,stage,unit); ex.parent.mkdir(parents=True,exist_ok=True); from .gates import _dep_fingerprint
 fp=hashlib.sha256(json.dumps(_dep_fingerprint(project,m,stage,unit),sort_keys=True).encode()).hexdigest(); write_text(ex,json.dumps({'unit':unit,'files':manifest,'input_fingerprint':fp,'proposal_id':p['proposal_id']},indent=2)+'\n')
 p['status']='accepted'; p['accepted_at']=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(); write_text(proposal_path(project,'implementation',unit,m),json.dumps(p,ensure_ascii=False,indent=2)+'\n')
 from .registry import add_event
 add_event(project,'human-approved-ai-implementation','implementation:'+unit,{'proposal_id':p['proposal_id'],'files':manifest})
 return manifest
