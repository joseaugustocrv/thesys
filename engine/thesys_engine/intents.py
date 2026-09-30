from pathlib import Path
import json
from .errors import ProjectError
from .project import project_language
from .io import read_text,write_text
from .registry import add_event
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
  from .templates import render_template
  language=project_language(project, methodology.language)
  pt=language.lower().startswith('pt-')
  sections={
   'purpose': statement.strip(),
   'desired-outcome': (outcome or statement).strip(),
   'users-and-stakeholders': '',
   'scope': '',
   'in-scope': '',
   'out-of-scope': '',
   'success-signals': '',
   'constraints': '',
   'assumptions': '',
   'open-questions': '',
  }
  content=render_template(methodology,'intent',sections,language,'default')
 p.parent.mkdir(parents=True,exist_ok=True); write_text(p,content.rstrip()+'\n'); add_event(project,'human-intent-input-created','default',{'path':str(INPUT),'owner':owner}); return p

def read_intent_input(project):
 p=project/INPUT
 if not p.is_file(): raise ProjectError('Intent input not found. Run thesys intent create first.')
 return read_text(p)

def propose_discovery(project,methodology,provider='openai'):
 from .gates import status
 intent_status = status(project, methodology).get('intent', {}).get('status')
 if intent_status in {'approved', 'completed'}:
  raise ProjectError('Intent is already authoritative. Use the lifecycle next action to work on the current stage; discovery is only for the pre-approval Intent flow.')
 source=read_intent_input(project); answers=_load_answers(project)
 agent=get_agent(provider); result=agent.propose_discovery(methodology,source,answers,project)
 language=project_language(project, methodology.language)
 from .templates import render_template
 from .proposals import _validate_generated_content, _validate_artifact_refs
 intent_content=render_template(methodology,'intent',result.get('intent_sections',{}),language,'default')
 context=render_template(methodology,'context',result.get('context_sections',{}),language,'default')
 intent_content=_validate_generated_content(intent_content,language)
 intent_content=_validate_artifact_refs(project,methodology,intent_content)
 context=_validate_generated_content(context,language)
 questions=[{**q,'question':str(q.get('question','')).strip(),'why':str(q.get('why','')).strip()} for q in result.get('questions',[])]
 inputs={'intent_input':source,'answers':answers,'project_template':str((project/'.thesys/project.yaml').read_text(encoding='utf-8'))}
 p=save_proposal(project,'intent','default',agent.name,intent_content,questions,inputs,metadata={'discovery_context': context})
 return p

def read_discovery_proposal(project):
 p=proposal_path(project,'intent','default')
 if not p.is_file(): raise ProjectError('Discovery proposal not found. Run thesys discovery propose first.')
 import json
 data=json.loads(read_text(p))
 if isinstance(data.get('content'), str):
  try:
   body=json.loads(data['content'])
  except json.JSONDecodeError:
   body={'intent': data['content'], 'context': data.get('discovery_context', '')}
 else:
  body=data.get('content') or {}
 return data,body

def accept_discovery(project,methodology):
 from .workflow import proposal_questions
 data,body=read_discovery_proposal(project)
 if data.get('status')!='proposed': raise ProjectError('Discovery proposal is not current; regenerate it before approval.')
 if proposal_questions(project,data): raise ProjectError('Blocking discovery questions remain unanswered.')
 if data.get('input_fingerprint') != __import__('hashlib').sha256(__import__('json').dumps({'intent_input':read_intent_input(project),'answers':_load_answers(project),'project_template':str((project/'.thesys/project.yaml').read_text(encoding='utf-8'))},ensure_ascii=False,sort_keys=True).encode()).hexdigest():
  raise ProjectError('Discovery proposal is stale. Regenerate it.')
 ip=project/INTENT; ip.parent.mkdir(parents=True,exist_ok=True)
 intent_content = body.get('intent', '')
 write_text(ip, intent_content.rstrip() + '\n')
 from .gates import approve
 approve(project,methodology,'intent','default',proposal_id=data['proposal_id'])
 from .registry import add_event
 add_event(project,'discovery-accepted','default',{'proposal_id':data['proposal_id']})
 return ip,None

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
