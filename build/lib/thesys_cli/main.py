import argparse, json, os, shlex, subprocess
from pathlib import Path
from thesys_engine import __version__
from thesys_engine.methodology import load_methodology
from thesys_engine.project import init_project,config,set_config,create_unit,unit_info,project_info,resolve_project,set_active_project,is_project,validate_project_key
from thesys_engine.project_templates import load_project_templates
from thesys_engine.gates import status,next_stage
from thesys_engine.errors import ProjectError,ThesysError
from thesys_engine.intents import create_intent,propose_discovery,read_discovery_proposal,accept_discovery
from thesys_engine.workflow import answer_question,load_proposal,proposal_questions,accept_proposal,proposal_path
from thesys_engine.proposals import generate,list_proposals
from thesys_engine.implementation import propose as propose_implementation,accept as accept_implementation,read_impl_proposal
from thesys_engine.agents import get_agent,GenerationContext
from thesys_engine.io import read_text,write_text
from thesys_engine.registry import get
from thesys_engine.evidence import record
from thesys_engine.changes import create_change,impact
from thesys_engine.traceability import graph

# The two imports above intentionally avoid optional legacy symbols in older installations.

def _workspace(path,repo):
    env=os.getenv('THESYS_WORKSPACE')
    if env: return Path(env).expanduser().resolve()
    cwd=Path(path).resolve()
    if (cwd/'pyproject.toml').is_file() and 'name = "thesys"' in cwd.joinpath('pyproject.toml').read_text(encoding='utf8'):
        return (cwd.parent/'Thesys Projects').resolve()
    return cwd

def _load_dotenv(project,extra):
    for p in (project/'.env',extra/'.env'):
        if not p.is_file(): continue
        for line in p.read_text(encoding='utf8').splitlines():
            line=line.strip()
            if line and not line.startswith('#') and '=' in line:
                k,v=line.split('=',1); os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))

def _provider(project,explicit): return explicit or config(project).get('agent_provider','openai')
def _require_project(path):
    if not is_project(path): raise ProjectError(f'Not a Thesys project: {path}')
def _list_projects(root):
    if is_project(root): return [root]
    return [p for p in sorted(root.iterdir()) if p.is_dir() and is_project(p)] if root.exists() else []

def _ctx(project,m,unit):
    from thesys_engine.workflow import stage_unit
    from thesys_engine.gates import status
    st=status(project,m,unit); approved={}
    for s in m.stages:
        p=m.artifact_path(project,s,stage_unit(m,s,unit))
        if p and p.is_file() and st.get(s.id,{}).get('status') in {'approved','completed'}: approved[s.id]=read_text(p)
    from thesys_engine.project import unit_info
    from thesys_engine.workflow import _load_answers
    return GenerationContext(approved.get('intent',''),unit,unit_info(project,unit)['scope'],m.language,approved,_load_answers(project))

def main(argv=None):
    parser=argparse.ArgumentParser(prog='thesys'); parser.add_argument('--version',action='version',version=__version__); sub=parser.add_subparsers(dest='command')
    init=sub.add_parser('init'); init.add_argument('--path',default='.'); init.add_argument('--name'); init.add_argument('--template',default='software-system')
    project=sub.add_parser('project'); ps=project.add_subparsers(dest='project_command')
    p=ps.add_parser('create'); p.add_argument('key'); p.add_argument('--name'); p.add_argument('--template'); p.add_argument('--path',default='.')
    p=ps.add_parser('list'); p.add_argument('--path',default='.')
    p=ps.add_parser('info'); p.add_argument('key',nargs='?'); p.add_argument('--path',default='.')
    p=ps.add_parser('use'); p.add_argument('key'); p.add_argument('--path',default='.')
    p=ps.add_parser('templates'); p.add_argument('--path',default='.')
    for n in ('status','validate','next'):
        p=sub.add_parser(n); p.add_argument('--path',default='.'); p.add_argument('--unit',default='default')
    it=sub.add_parser('intent'); its=it.add_subparsers(dest='intent_command')
    p=its.add_parser('create'); p.add_argument('statement',nargs='?'); p.add_argument('--outcome',default=''); p.add_argument('--owner',default='Human owner'); p.add_argument('--file'); p.add_argument('--path',default='.')
    ip=sub.add_parser('discovery'); ips=ip.add_subparsers(dest='discovery_command')
    p=ips.add_parser('propose'); p.add_argument('--agent'); p.add_argument('--path',default='.')
    p=ips.add_parser('show'); p.add_argument('--path',default='.')
    p=ips.add_parser('accept'); p.add_argument('--path',default='.')
    q=sub.add_parser('question'); qs=q.add_subparsers(dest='question_command')
    p=qs.add_parser('list'); p.add_argument('--path',default='.'); p.add_argument('--unit',default='default')
    p=qs.add_parser('answer'); p.add_argument('id'); p.add_argument('answer'); p.add_argument('--path',default='.')
    u=sub.add_parser('unit'); us=u.add_subparsers(dest='unit_command')
    p=us.add_parser('create'); p.add_argument('key'); p.add_argument('name'); p.add_argument('--scope',default=''); p.add_argument('--type',default='feature'); p.add_argument('--parent',default='default'); p.add_argument('--path',default='.')
    p=us.add_parser('list'); p.add_argument('--path',default='.')
    p=us.add_parser('propose'); p.add_argument('--agent'); p.add_argument('--path',default='.')
    p=us.add_parser('proposal'); ups=p.add_subparsers(dest='unit_proposal_command'); x=ups.add_parser('accept'); x.add_argument('--path',default='.')
    g=sub.add_parser('generate'); g.add_argument('stage'); g.add_argument('--unit',default='default'); g.add_argument('--agent'); g.add_argument('--path',default='.')
    pr=sub.add_parser('proposal'); prs=pr.add_subparsers(dest='proposal_command')
    p=prs.add_parser('list'); p.add_argument('--path',default='.')
    p=prs.add_parser('show'); p.add_argument('stage'); p.add_argument('--unit',default='default'); p.add_argument('--path',default='.')
    p=prs.add_parser('accept'); p.add_argument('stage'); p.add_argument('--unit',default='default'); p.add_argument('--path',default='.')
    impl=sub.add_parser('implementation'); ims=impl.add_subparsers(dest='implementation_command')
    p=ims.add_parser('propose'); p.add_argument('--unit',default='default'); p.add_argument('--agent'); p.add_argument('--path',default='.')
    p=ims.add_parser('show'); p.add_argument('--unit',default='default'); p.add_argument('--path',default='.')
    p=ims.add_parser('accept'); p.add_argument('--unit',default='default'); p.add_argument('--path',default='.')
    v=sub.add_parser('verify'); v.add_argument('--unit',default='default'); v.add_argument('--agent'); v.add_argument('--path',default='.')
    tr=sub.add_parser('trace'); tr.add_argument('artifact_id'); tr.add_argument('--path',default='.')
    ev=sub.add_parser('evidence'); evs=ev.add_subparsers(dest='evidence_command'); p=evs.add_parser('record'); p.add_argument('subject'); p.add_argument('result'); p.add_argument('--type',default='verification'); p.add_argument('--source',default='cli'); p.add_argument('--related',default=''); p.add_argument('--path',default='.')
    ch=sub.add_parser('change'); chs=ch.add_subparsers(dest='change_command'); p=chs.add_parser('create'); p.add_argument('unit'); p.add_argument('title'); p.add_argument('description'); p.add_argument('--path',default='.'); p=chs.add_parser('impact'); p.add_argument('change_id'); p.add_argument('--path',default='.')
    c=sub.add_parser('config'); cs=c.add_subparsers(dest='config_command'); p=cs.add_parser('get'); p.add_argument('--path',default='.'); p=cs.add_parser('set'); p.add_argument('key'); p.add_argument('value'); p.add_argument('--path',default='.')

    a=parser.parse_args(argv); repo=Path(__file__).resolve().parents[2];
    if not (repo/'methodology/definition/lifecycle.md').is_file():
        repo=Path(__file__).resolve().parents[1]/'thesys_engine'/'bundle'
    m=load_methodology(repo); raw=_workspace(getattr(a,'path','.'),repo); _load_dotenv(raw,Path.cwd())
    if a.command=='project':
        if a.project_command=='create':
            validate_project_key(a.key); dest=(raw/a.key).resolve(); dest.relative_to(raw);
            if dest.exists() and any(dest.iterdir()): raise ProjectError(f'Project destination is not empty: {dest}')
            init_project(dest,m,a.template,a.name,a.key); set_active_project(raw,dest); print(f'Thesys project created: {dest}'); print(f'Active project: {a.key}'); return 0
        if a.project_command=='list':
            for p in _list_projects(raw):
                i=project_info(p); print(f"{i.get('key')}\t{i.get('name')}\t{i.get('template')}\t{p}")
            return 0
        if a.project_command=='info':
            p=resolve_project(raw,a.key); [print(f'{k}={v}') for k,v in project_info(p).items()]; return 0
        if a.project_command=='use':
            p=resolve_project(raw,a.key); set_active_project(raw,p); print(f'Active project: {a.key}'); print(f'Path: {p}'); return 0
        if a.project_command=='templates':
            for k,x in sorted(load_project_templates(repo).items()): print(f'{k}\t{x.name}\t{x.description}')
            return 0
    if a.command=='init': init_project(Path(a.path).resolve(),m,a.template,a.name,Path(a.path).name); print(f'Thesys project initialized: {Path(a.path).resolve()}'); return 0
    if a.command in {'status','validate','next','intent','discovery','question','unit','generate','proposal','implementation','verify','trace','evidence','change','config'}:
        p=resolve_project(raw); _load_dotenv(p,p.parent)
    else: p=None
    if a.command=='intent' and a.intent_command=='create': print(f'Intent input created: {create_intent(p,a.statement,a.outcome,a.owner,a.file,m)}'); return 0
    if a.command=='discovery':
        if a.discovery_command=='propose': print(f'Discovery proposal generated: {propose_discovery(p,m,_provider(p,a.agent))}'); return 0
        if a.discovery_command=='show':
            data,body=read_discovery_proposal(p); print(json.dumps(data,ensure_ascii=False,indent=2)); print('\n--- PROPOSAL ---\n'); print(json.dumps(body,ensure_ascii=False,indent=2)); return 0
        if a.discovery_command=='accept': print(f'Discovery accepted: {accept_discovery(p,m)[0]}'); return 0
    if a.command=='question':
        if a.question_command=='answer': answer_question(p,a.id,a.answer); print(f'Question answered: {a.id}'); return 0
        if a.question_command=='list':
            from thesys_engine.workflow import _load_answers
            answers=_load_answers(p)
            for f in list_proposals(p):
                try:
                    d=json.loads(read_text(f))
                    for q in d.get('questions',[]): print(f"{q['id']}\t{'answered' if q['id'] in answers else 'open'}\t{'blocking' if q.get('blocking') else 'non-blocking'}\t{q['question']}")
                except Exception: pass
            return 0
    if a.command=='unit':
        if a.unit_command=='create':
            if status(p,m)['intent']['status']!='approved': raise ProjectError('Engineering units can only be created after the authoritative Intent is approved.')
            print(f'Engineering unit created: {create_unit(p,a.key,a.name,a.scope,a.type,a.parent,m)}'); return 0
        if a.unit_command=='list':
            for f in sorted((p/'.thesys/units').glob('*.json')): x=json.loads(read_text(f)); print(f"{f.stem}\t{x.get('type')}\t{x.get('parent')}")
            return 0
        if a.unit_command=='propose':
            from thesys_engine.unit_proposals import generate_unit_proposal
            print(f'Engineering unit proposal generated: {generate_unit_proposal(p,_provider(p,a.agent))}'); return 0
        if a.unit_command=='proposal' and a.unit_proposal_command=='accept':
            from thesys_engine.unit_proposals import accept_unit_proposal
            for x in accept_unit_proposal(p,m): print(f'Engineering unit created: {x}')
            return 0
    if a.command in {'status','next','validate'}:
        if a.command=='status':
            st=status(p,m,a.unit); [print(f'{s.id}: {st[s.id]["status"]}') for s in m.stages]; return 0
        if a.command=='next':
            s=next_stage(p,m,a.unit); print(f'Next lifecycle stage: {s.id if s else "none"}'); return 0
        from thesys_engine.validate import validate
        findings=validate(p,m); [print('ERROR: '+x) for x in findings]; print('Thesys project validation passed.' if not findings else 'Thesys project validation failed.'); return 0 if not findings else 1
    if a.command=='generate':
        print(f'Proposal generated: {generate(p,m,a.stage,a.unit,_provider(p,a.agent))}'); return 0
    if a.command=='proposal':
        if a.proposal_command=='list': [print(x) for x in list_proposals(p)]; return 0
        if a.proposal_command=='show': print(json.dumps(load_proposal(p,a.stage,a.unit),ensure_ascii=False,indent=2)); return 0
        if a.proposal_command=='accept': print(f'Authoritative artifact created: {accept_proposal(p,m,a.stage,a.unit)}'); return 0
    if a.command=='implementation':
        if a.implementation_command=='propose': print(f'Implementation proposal generated: {propose_implementation(p,m,a.unit,_provider(p,a.agent))}'); return 0
        if a.implementation_command=='show': print(json.dumps(read_impl_proposal(p,a.unit),ensure_ascii=False,indent=2)); return 0
        if a.implementation_command=='accept': print('Implementation applied:'); [print('- '+x) for x in accept_implementation(p,m,a.unit)]; return 0
    if a.command=='verify':
        stage=m.stage('verification'); from thesys_engine.workflow import authoritative_inputs,save_proposal
        from thesys_engine.evidence import record
        command=stage.config.get('command','python -m pytest -q'); result=subprocess.run(shlex.split(command),cwd=p,text=True,capture_output=True); output=result.stdout or result.stderr
        record(p,f'verification:{a.unit}','PASS' if result.returncode==0 else 'FAIL',related=[])
        c=_ctx(p,m,a.unit); c=GenerationContext(c.intent,c.unit,c.unit_scope,c.language,{**c.approved_artifacts,'verification_execution':output},c.answers); ai=get_agent(_provider(p,a.agent)); proposal=ai.propose_document(m,'verification',c); qs=proposal.get('questions',[])
        if result.returncode!=0: qs.append({'id':'QST-VER-001','question':'Verification command failed. Resolve the failing verification before accepting this proposal.','why':'A failed verification cannot establish conformity.','blocking':True})
        inputs=authoritative_inputs(p,m,stage,a.unit); save_proposal(p,'verification',a.unit,ai.name,proposal['content'],qs,inputs); print(f'Verification proposal generated: {proposal_path(p,"verification",a.unit)}'); return 0 if result.returncode==0 else 1
    if a.command=='trace':
        data=get(p); root=data.get('artifacts',{}).get(a.artifact_id)
        if not root: print(f'Artifact not found: {a.artifact_id}'); return 1
        print(f"{a.artifact_id}: {root.get('type')} [{root.get('status')}] {root.get('path')}"); [print(f"  {e['relation']} -> {e['target']}") for e in graph(p,a.artifact_id)]; return 0
    if a.command=='evidence' and a.evidence_command=='record':
        print(f"Evidence recorded: {record(p,a.subject,a.result,a.type,a.source,related=[x for x in a.related.split(',') if x])}"); return 0
    if a.command=='change':
        if a.change_command=='create': print(f'Change created: {create_change(p,a.title,a.description,a.unit)}'); return 0
        if a.change_command=='impact': [print(f"{e['source']} --{e['relation']}--> {e['target']}") for e in impact(p,a.change_id)]; return 0
    if a.command=='config':
        if a.config_command=='get': [print(f'{k}={v}') for k,v in config(p).items()]
        else: set_config(p,a.key,a.value); print(f'Configuration updated: {a.key}={a.value}')
        return 0
    parser.print_help(); return 2

if __name__=='__main__':
    try: raise SystemExit(main())
    except (ProjectError,ThesysError,RuntimeError,ValueError,OSError) as exc: print(f'ERROR: {exc}'); raise SystemExit(1)
