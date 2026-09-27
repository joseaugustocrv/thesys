from pathlib import Path
import json
from .errors import ProjectError
from .io import read_text,write_text
from .registry import add_event
from .templates import load_template
from .agents import get_agent
from .workflow import save_proposal,proposal_path,answer_path,_load_answers

INPUT=Path('engineering/intent/input.md')
INTENT=Path('engineering/intent/intent.md')
CONTEXT=Path('engineering/context/default/context.md')

def create_intent(project,statement,outcome='',owner='Human owner',source_file=None,methodology=None):
 p=project/INPUT
 if p.exists() or (project/INTENT).exists(): raise ProjectError('An Intent already exists. Create a change to revise an authoritative Intent.')
 if source_file:
  src=Path(source_file)
  if not src.is_file(): raise ProjectError(f'Intent source file not found: {src}')
  content=read_text(src)
 else:
  if not statement or not statement.strip(): raise ProjectError('Intent statement cannot be empty.')
  if methodology is None: raise ProjectError('Methodology is required to create an Intent.')
  content=load_template(methodology,'intent')
  content=content.replace('Describe the problem or opportunity that motivates the project or change.',statement.strip())
  content=content.replace('Describe the outcome that should exist when the intent is satisfied.',(outcome or statement).strip())
  content=content.replace('[Owner]',owner)
 p.parent.mkdir(parents=True,exist_ok=True); write_text(p,content.rstrip()+'\n'); add_event(project,'human-intent-input-created','default',{'path':str(INPUT),'owner':owner}); return p

def read_intent_input(project):
 p=project/INPUT
 if not p.is_file(): raise ProjectError('Intent input not found. Run thesys intent create first.')
 return read_text(p)

def propose_discovery(project,methodology,provider='openai'):
 source=read_intent_input(project); answers=_load_answers(project)
 agent=get_agent(provider); result=agent.propose_discovery(methodology,source,answers,project)
 content=result['intent']; context=result['context']; questions=result.get('questions',[])
 inputs={'intent_input':source,'answers':answers,'project_template':str((project/'.thesys/project.yaml').read_text(encoding='utf-8'))}
 # Store the combined proposal in the intent proposal. Context is part of the same human approval decision.
 p=save_proposal(project,'intent','default',agent.name,json.dumps({'intent':content,'context':context},ensure_ascii=False,indent=2),questions,inputs)
 return p

def read_discovery_proposal(project):
 p=proposal_path(project,'intent','default')
 if not p.is_file(): raise ProjectError('Discovery proposal not found. Run thesys discovery propose first.')
 import json
 data=json.loads(read_text(p)); body=json.loads(data['content']); return data,body

def accept_discovery(project,methodology):
 from .workflow import proposal_questions
 data,body=read_discovery_proposal(project)
 if data.get('status')!='proposed': raise ProjectError('Discovery proposal is not current; regenerate it before approval.')
 if proposal_questions(project,data): raise ProjectError('Blocking discovery questions remain unanswered.')
 from .gates import status
 if data.get('input_fingerprint') != __import__('hashlib').sha256(__import__('json').dumps({'intent_input':read_intent_input(project),'answers':_load_answers(project),'project_template':str((project/'.thesys/project.yaml').read_text(encoding='utf-8'))},ensure_ascii=False,sort_keys=True).encode()).hexdigest():
  raise ProjectError('Discovery proposal is stale. Regenerate it.')
 ip=project/INTENT; cp=project/CONTEXT; ip.parent.mkdir(parents=True,exist_ok=True); cp.parent.mkdir(parents=True,exist_ok=True)
 def _mark_authoritative(content):
  lines=[]
  for line in content.splitlines():
   normalized=line.casefold()
   if 'status da proposta:' in normalized:
    line='**Status da proposta:** Autoritativa.'
   elif normalized.startswith('**status:**'):
    line='**Status:** Authoritative'
   elif normalized.startswith('status:'):
    line='Status: Authoritative'
   lines.append(line)
  return '\n'.join(lines).rstrip()+'\n'
 write_text(ip,_mark_authoritative(body['intent'])); write_text(cp,_mark_authoritative(body['context']))
 from .gates import approve
 # Context is the discovery result and is approved together with Intent by the same human action.
 approve(project,methodology,'intent','default',proposal_id=data['proposal_id'])
 # Context has a distinct artifact/approval record, using the same proposal as evidence of human approval.
 import hashlib,json
 state=json.loads(read_text(project/'.thesys/approvals.json')); from .gates import _dep_fingerprint
 state['approvals']['context:default']={'sha256':hashlib.sha256(cp.read_bytes()).hexdigest(),'dependencies':_dep_fingerprint(project,methodology,methodology.stage('context'),'default'),'proposal_id':data['proposal_id'],'approved_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}; write_text(project/'.thesys/approvals.json',json.dumps(state,ensure_ascii=False,indent=2)+'\n')
 from .registry import allocate_id,register_artifact,add_event
 register_artifact(project,allocate_id(project,'CTX'),'CTX',cp,'default',status='authoritative',authority='human')
 add_event(project,'discovery-accepted','default',{'proposal_id':data['proposal_id']})
 return ip,cp

# Backward-compatible aliases for existing callers.
def propose_intent(project,methodology,provider='openai'): return propose_discovery(project,methodology,provider)
def read_intent_proposal(project): return read_discovery_proposal(project)
def accept_intent_proposal(project,methodology): return accept_discovery(project,methodology)[0]
def read_intent(project):
 p=project/INTENT
 if not p.is_file(): raise ProjectError('Authoritative Intent not found. Accept the AI discovery proposal first.')
 return read_text(p)
def intent_digest(project):
 import hashlib
 return hashlib.sha256(read_intent(project).encode()).hexdigest()
