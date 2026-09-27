from dataclasses import dataclass
import json,os
from .errors import ThesysError
from .templates import load_template

@dataclass(frozen=True)
class GenerationContext:
    intent:str
    unit:str
    unit_scope:str
    language:str
    approved_artifacts:dict
    answers:dict

class Agent:
    name='unknown'
    def propose_discovery(self,*a,**k): raise NotImplementedError
    def propose_document(self,*a,**k): raise NotImplementedError
    def propose_code(self,*a,**k): raise NotImplementedError

class MockAgent(Agent):
    name='mock'
    def propose_discovery(self,m,human_input,answers,project):
        # Deterministic fixture: questions are driven by explicit tokens so tests can exercise the real question loop.
        questions=[]
        if '[[QUESTION:' in human_input and not answers:
            questions=[{'id':'QST-001','question':'Please provide the missing business constraint represented by [[QUESTION:...]].','why':'The initial Intent explicitly signals missing information.','blocking':True}]
        intent=human_input.strip()+'\n\n## Intent refinement\n\n- The authoritative intent will be established only after human approval of this proposal.\n'
        context='# Engineering Context — default\n\n## System and unit boundary\n\n- System: The system described by the human Intent.\n- Unit type: system\n- In scope: As stated in the Intent.\n\n## Existing state\n\nThe initial state is not assumed beyond the information provided by the human.\n\n## Dependencies\n\nNo dependency is asserted without evidence.\n\n## Stakeholders and concerns\n\nDerived only from the Intent; unknown stakeholders remain unknown.\n\n## Environments\n\nTo be determined during engineering discovery.\n\n## Applicable standards and policies\n\nThe methodology requires applicable quality, security and lifecycle controls to be assessed in later stages.\n\n## Open questions\n\nNone beyond the proposal questions.\n\nStatus: Proposed\n'
        if answers:
            context+='\n## Human answers incorporated\n\n'+ '\n'.join(f'- {k}: {v["answer"]}' for k,v in sorted(answers.items()))+'\n'
        return {'intent':intent,'context':context,'questions':questions}
    def propose_document(self,m,stage,c):
        t=load_template(m,stage,c.language)
        reps={'[Unit key]':c.unit,'[Owner]':'Human owner','[Item]':f'Work within approved scope of {c.unit}.','[Question]':'No blocking question identified by the deterministic provider.','[Expected result]':'The approved behavior is satisfied and verified.','[Evidence]':'Runtime verification evidence.','[Decision]':'Follow approved upstream artifacts.','[Constraint]':'Approved project constraints.','[Outcome]':'The approved intended outcome is achieved.','[Pass / Fail / Blocked]':'Pass'}
        for a,b in reps.items(): t=t.replace(a,b)
        return {'content':t,'questions':[]}
    def propose_code(self,m,c):
        return {'files':{'src/main.py':'def main():\n    return {"status": "ok"}\n','tests/test_main.py':'from src.main import main\n\ndef test_main():\n    assert main()["status"] == "ok"\n'},'questions':[]}

class OpenAIAgent(Agent):
    name='openai'
    def __init__(self,client=None):
        if client is not None: self.client=client
        else:
            try: from openai import OpenAI
            except ImportError as exc: raise ThesysError('The OpenAI SDK is not installed.') from exc
            key=os.getenv('OPENAI_API_KEY')
            if not key: raise ThesysError('OPENAI_API_KEY is not configured.')
            self.client=OpenAI(api_key=key)
        self.model=os.getenv('THESYS_OPENAI_MODEL','gpt-5.6-luna')
    def _call(self,instructions,input_text,schema,name):
        try:
            r=self.client.responses.create(model=self.model,instructions=instructions,input=input_text,text={'format':{'type':'json_schema','name':name,'strict':True,'schema':schema}})
            return json.loads(r.output_text)
        except Exception as exc: raise ThesysError(f'OpenAI request failed: {exc}') from exc
    def propose_discovery(self,m,human_input,answers,project):
        schema={'type':'object','properties':{'intent':{'type':'string','minLength':200},'context':{'type':'string','minLength':200},'questions':{'type':'array','items':{'type':'object','properties':{'id':{'type':'string'},'question':{'type':'string'},'why':{'type':'string'},'blocking':{'type':'boolean'}},'required':['id','question','why','blocking'],'additionalProperties':False}}},'required':['intent','context','questions'],'additionalProperties':False}
        instructions=('Act as the Thesys discovery engineer. The human supplies the only initial authority. Transform it into a proposed Intent and Engineering Context. '
                      'Discovery defines intent, not detailed requirements, specification, architecture, implementation, or operational procedures. Ask a focused question only when an unanswered issue changes an intent-level decision: purpose, desired outcome, scope boundary, primary users or stakeholders, material business constraint, high-level regulatory applicability, or measurable success criterion. '
                      'Do not continue questioning merely to make the proposal implementation-ready. Do not ask for downstream detail such as exact cloud regions/services, database fields or models, retention periods by data class, API/provider configuration, detailed permission matrices, exact subscription state machines, detailed measurement procedures, technical controls, or other decisions that belong in Requirements, Specification, Architecture, or later stages. '
                      'If the remaining unknowns can be resolved downstream without changing the intent, treat Discovery as converged and return no new questions. Do not invent facts. Preserve explicit human intent. Distinguish known facts, assumptions, and unknowns. The proposal is non-authoritative and requires human approval. If previous human answers exist, incorporate them and ask only remaining intent-level questions.')
        inp=f'Human Intent Input:\n{human_input}\n\nPrevious human answers:\n{json.dumps(answers,ensure_ascii=False,indent=2)}\n\nProject metadata:\n{(project/".thesys/project.yaml").read_text(encoding="utf-8")}\n\nIntent template:\n{load_template(m,"intent")}\n\nContext template:\n{load_template(m,"context")}'; return self._call(instructions,inp,schema,'thesys_discovery')
    def propose_document(self,m,stage,c):
        schema={'type':'object','properties':{'content':{'type':'string','minLength':200},'questions':{'type':'array','items':{'type':'object','properties':{'id':{'type':'string'},'question':{'type':'string'},'why':{'type':'string'},'blocking':{'type':'boolean'}},'required':['id','question','why','blocking'],'additionalProperties':False}}},'required':['content','questions'],'additionalProperties':False}
        instructions=('Produce a non-authoritative Thesys artifact proposal for the requested lifecycle stage. Use only authoritative inputs and answered questions. Do not invent facts, decisions, approvals, evidence, technologies or test results. Identify material uncertainty as explicit questions. Ask the human only questions that materially affect the stage.')
        inp=f'Stage: {stage}\nUnit: {c.unit}\nScope: {c.unit_scope}\nAuthoritative artifacts:\n{json.dumps(c.approved_artifacts,ensure_ascii=False,indent=2)}\nHuman answers:\n{json.dumps(c.answers,ensure_ascii=False,indent=2)}\nTemplate:\n{load_template(m,stage,c.language)}'; return self._call(instructions,inp,schema,'thesys_stage_proposal')
    def propose_code(self,m,c):
        schema={'type':'object','properties':{'files':{'type':'array','items':{'type':'object','properties':{'path':{'type':'string'},'content':{'type':'string'}},'required':['path','content'],'additionalProperties':False}},'questions':{'type':'array','items':{'type':'object','properties':{'id':{'type':'string'},'question':{'type':'string'},'why':{'type':'string'},'blocking':{'type':'boolean'}},'required':['id','question','why','blocking'],'additionalProperties':False}}},'required':['files','questions'],'additionalProperties':False}
        instructions=('Generate a non-authoritative implementation proposal from the approved engineering artifacts. Return only relative paths under the methodology allowed roots. Never include secrets. Do not claim tests were executed. If implementation depends on a material unknown, ask a blocking question instead of guessing.')
        inp=f'Unit: {c.unit}\nScope: {c.unit_scope}\nAuthoritative artifacts:\n{json.dumps(c.approved_artifacts,ensure_ascii=False,indent=2)}\nHuman answers:\n{json.dumps(c.answers,ensure_ascii=False,indent=2)}'; return self._call(instructions,inp,schema,'thesys_implementation_proposal')

def get_agent(name):
    if name=='mock': return MockAgent()
    if name=='openai': return OpenAIAgent()
    raise ThesysError(f'Unknown agent provider: {name}')
