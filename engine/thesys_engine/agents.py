from dataclasses import dataclass, field
import json, os
from .errors import ThesysError
from .templates import template_contract, template_schema, render_template
from .project import project_language


@dataclass(frozen=True)
class GenerationContext:
    intent: str
    unit: str
    unit_scope: str
    language: str
    approved_artifacts: dict
    answers: dict
    related_units: dict = field(default_factory=dict)
    unit_type: str = 'system'
    unit_parent: str | None = None
    unit_dependencies: tuple = ()
    clarification_history: list = field(default_factory=list)
    artifact_index: dict = field(default_factory=dict)
    human_guidance: dict = field(default_factory=dict)




def _question_schema():
    """Return the agent-facing clarification-question contract.

    Question identity is intentionally absent: IDs belong to the Thesys
    runtime and are allocated after the model response is validated.
    """
    return {
        "type": "object",
        "properties": {
            "question": {"type": "string", "minLength": 1},
            "why": {"type": "string", "minLength": 1},
            "blocking": {"type": "boolean"},
        },
        "required": ["question", "why", "blocking"],
        "additionalProperties": False,
    }

def _lifecycle_question_context(methodology, current_stage):
    """Build the model-facing lifecycle contract for question classification."""
    stages = []
    for stage in methodology.stages:
        stages.append({
            "id": stage.id,
            "name": stage.name,
            "depends_on": list(stage.depends_on),
            "action": stage.action,
            "scope": stage.config.get("scope", "unit"),
            "artifact": stage.artifact,
            "template_sections": list(template_schema(methodology, stage.id).keys()),
        })
    return {
        "current_stage": current_stage,
        "stages": stages,
        "rules": {
            "human_approval_required_before_progression": methodology.rules.get("human_approval_required_before_progression", True),
            "unresolved_questions_block_affected_gate": methodology.rules.get("unresolved_questions_block_affected_gate", True),
            "question_blocking": methodology.rules.get("question_blocking", {}),
            "human_guidance_is_optional": methodology.rules.get("human_guidance_is_optional", True),
            "human_guidance_is_non_authoritative": methodology.rules.get("human_guidance_is_non_authoritative", True),
            "human_guidance_propagates_downstream": methodology.rules.get("human_guidance_propagates_downstream", True),
        },
    }


class Agent:
    name = 'unknown'
    def propose_discovery(self, *a, **k): raise NotImplementedError
    def propose_document(self, *a, **k): raise NotImplementedError
    def propose_code(self, *a, **k): raise NotImplementedError


def _generic_sections(methodology, stage, language, unit, entity_label="Unit"):
    contract = template_contract(methodology, stage)
    pt = language.lower().startswith('pt-')
    sections = {}
    for section in contract.sections:
        if section.id.endswith('status'):
            sections[section.id] = '**Status:** Rascunho' if pt else '**Status:** Draft'
        else:
            sections[section.id] = (
                f'Conteúdo proposto para a seção do {entity_label} {unit}.' if pt else
                f'Proposed content for the {entity_label} {unit}.'
            )
    return sections


class MockAgent(Agent):
    name = 'mock'

    def propose_discovery(self, m, human_input, answers, project, guidance=None):
        language = project_language(project, m.language)
        pt = language.lower().startswith('pt-')
        intent_contract = template_contract(m, 'intent')
        context_contract = template_contract(m, 'context')
        intent = {s.id: '' for s in intent_contract.sections}
        context = {s.id: '' for s in context_contract.sections}
        intent['purpose'] = human_input.strip()
        def answer_containing(*markers):
            for record in answers.values():
                question = str(record.get('question', '')).casefold()
                if all(marker.casefold() in question for marker in markers):
                    return record.get('answer', '')
            return ''

        users_answer = answer_containing('usuários', 'partes interessadas') or answer_containing('usuários')
        scope_answer = answer_containing('escopo')
        success_answer = answer_containing('sucesso') or answer_containing('resultado observável')
        constraints_answer = answer_containing('restrições') or answer_containing('regulat')
        guidance_text = '\n'.join(str(item.get('content', '')) for item in (guidance or {}).values() if item.get('content'))
        if guidance_text:
            constraints_answer = (constraints_answer + '\n' + guidance_text).strip()
        intent['desired-outcome'] = success_answer or human_input.strip()
        intent['users-and-stakeholders'] = users_answer
        intent['scope'] = scope_answer
        intent['in-scope'] = scope_answer
        intent['out-of-scope'] = scope_answer
        intent['success-signals'] = success_answer
        intent['constraints'] = constraints_answer
        intent['assumptions'] = 'Informações não fornecidas permanecem como desconhecidas.' if pt else 'Information not supplied remains unknown.'
        intent['open-questions'] = 'Nenhuma questão adicional identificada.' if pt else 'No additional questions identified.'
        intent['intent-status'] = 'Proposta não autoritativa.' if pt else 'Non-authoritative proposal.'

        context['system-and-unit-boundary'] = '- Sistema: conforme a Intenção.\n- Unidade pai: não aplicável.\n- Tipo de unidade: system.'
        context['existing-state'] = 'O estado atual não é presumido além das informações fornecidas.' if pt else 'The current state is not assumed beyond supplied information.'
        context['dependencies'] = 'Nenhuma dependência é afirmada sem evidência.' if pt else 'No dependency is asserted without evidence.'
        context['stakeholders-and-concerns'] = intent['users-and-stakeholders'] or ('Derivados da Intenção.' if pt else 'Derived from the Intent.')
        context['environments'] = 'A definir nas etapas apropriadas.' if pt else 'To be defined in the appropriate stages.'
        context['applicable-standards-and-policies'] = intent['constraints'] or ('A avaliar nas etapas apropriadas.' if pt else 'To be assessed in the appropriate stages.')
        context['open-questions'] = intent['open-questions']
        context['governing-intent'] = '`engineering/intent/intent.md`'
        questions = []
        if '[[QUESTION:' in human_input and not answers:
            questions = [{'question': 'Informe a restrição de negócio ausente representada por [[QUESTION:...]].' if pt else 'Please provide the missing business constraint represented by [[QUESTION:...]].', 'why': 'O Intent inicial sinaliza explicitamente informação ausente.' if pt else 'The initial Intent explicitly signals missing information.', 'blocking': True}]
        return {
            'intent_sections': intent,
            'context_sections': context,
            'questions': questions,
        }

    def propose_document(self, m, stage, c):
        entity_label = 'Projeto' if c.unit_type == 'project' and c.language.lower().startswith('pt-') else ('Project' if c.unit_type == 'project' else 'Unidade' if c.language.lower().startswith('pt-') else 'Unit')
        sections = _generic_sections(m, stage, c.language, c.unit, entity_label)
        if m.stage(stage).config.get('aggregate_units'):
            names = []
            for key, meta in sorted(c.related_units.items()):
                name = meta.get('name', key) if isinstance(meta, dict) else key
                names.append(f'- {name} ({key})')
            sections['engineering-unit-map'] = '\n'.join(names) if names else '- project'
        return {'sections': sections, 'questions': []}

    def propose_code(self, m, c):
        return {
            'files': {
                'src/main.py': 'def main():\n    return {"status": "ok"}\n',
                'tests/test_main.py': 'from src.main import main\n\ndef test_main():\n    assert main()["status"] == "ok"\n',
            },
            'questions': [],
        }


class OpenAIAgent(Agent):
    name = 'openai'

    def __init__(self, client=None):
        if client is not None:
            self.client = client
        else:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise ThesysError('The OpenAI SDK is not installed.') from exc
            key = os.getenv('OPENAI_API_KEY')
            if not key:
                raise ThesysError('OPENAI_API_KEY is not configured.')
            self.client = OpenAI(api_key=key)
        self.model = os.getenv('THESYS_OPENAI_MODEL', 'gpt-5.6-luna')

    def _call(self, instructions, input_text, schema, name):
        try:
            r = self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=input_text,
                text={'format': {'type': 'json_schema', 'name': name, 'strict': True, 'schema': schema}},
            )
            return json.loads(r.output_text)
        except Exception as exc:
            raise ThesysError(f'OpenAI request failed: {exc}') from exc

    def _prompt_catalog(self, methodology):
        path = methodology.root / "methodology" / "agents" / "prompts.json"
        if not path.is_file():
            raise ThesysError(f"Agent prompt catalog not found: {path}")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ThesysError(f"Invalid agent prompt catalog: {path}") from exc

    def _language_rule(self, language):
        return (
            f'Project language: {language}. All natural-language artifact content and all human-facing questions must be written in that language. '
            'The template defines the document structure and headings; do not generate Markdown headings, titles, section labels, template instructions, or placeholders. '
            'Return content only for the section keys defined by the JSON schema. Preserve identifiers, artifact IDs, paths and schema enum values exactly. '
            'Clarification question IDs (QST-NNN) are runtime-owned. Never reproduce them in artifact content or assign them to questions. '
            'This prohibition also applies when incorporating human answers, explaining resolved decisions, writing traceability sections, or describing the basis for a decision. '
            'Questions and their IDs belong exclusively to proposal metadata and clarification history. If a human answer resolves a question, incorporate the resulting decision directly without mentioning the question ID, question text, or clarification rationale. '
            'Never copy QST-NNN identifiers from the input, clarification history, human answers, or previous proposals into artifact content. '
            'For pt-BR, do not use English normative words such as shall, must or should in natural-language content.'
        )

    def _stage_prompt(self, methodology, stage):
        catalog = self._prompt_catalog(methodology)
        common = catalog.get('common', [])
        specific = catalog.get('stages', {}).get(stage, [])
        return ' '.join([*common, *specific])

    def propose_discovery(self, m, human_input, answers, project, guidance=None):
        language = project_language(project, m.language)
        intent_schema = template_schema(m, 'intent')
        context_schema = template_schema(m, 'context')
        schema = {
            'type': 'object',
            'properties': {
                'intent_sections': intent_schema,
                'context_sections': context_schema,
                'questions': {'type': 'array', 'items': _question_schema()},
            },
            'required': ['intent_sections','context_sections','questions'],
            'additionalProperties': False,
        }
        instructions = (
            self._language_rule(language) + ' ' +
            ' '.join(self._prompt_catalog(m).get('common', [])) + ' ' +
            ' '.join(self._prompt_catalog(m).get('discovery', [])) + ' ' +
            'Human guidance is optional and non-authoritative. Use applicable guidance to orient discovery, but never silently override an approved artifact or decision. If guidance conflicts materially with authoritative context, surface the conflict through a blocking question.' + ' ' +
            'Fill every section key with substantive content; an intentionally empty section is allowed only when the source genuinely does not support content.'
        )
        inp = (
            f'Human Intent Input:\n{human_input}\n\n'
            f'Previous human answers:\n{json.dumps(answers, ensure_ascii=False, indent=2)}\n\n'
            f'Human guidance applicable to discovery:\n{json.dumps(guidance or {}, ensure_ascii=False, indent=2)}\n\n'
            f'Project metadata:\n{(project/".thesys/project.yaml").read_text(encoding="utf-8")}\n\n'
            f'Intent structural contract:\n{json.dumps(template_schema(m,"intent"), ensure_ascii=False, indent=2)}\n\n'
            f'Context structural contract:\n{json.dumps(template_schema(m,"context"), ensure_ascii=False, indent=2)}'
        )
        return self._call(instructions, inp, schema, 'thesys_discovery_structured')

    def propose_document(self, m, stage, c):
        schema = {
            'type': 'object',
            'properties': {
                'sections': template_schema(m, stage),
                'questions': {'type': 'array', 'items': _question_schema()},
            },
            'required': ['sections','questions'],
            'additionalProperties': False,
        }
        language_rule = self._language_rule(c.language)
        integration_rule = ''
        if m.stage(stage).config.get('aggregate_units'):
            integration_rule = (
                ' For system-architecture, synthesize only from the approved Architecture artifacts supplied for the relevant Engineering Units. '
                'Preserve their boundaries and dependencies; do not invent unsupported system-level architecture.'
            )
        instructions = (
            self._stage_prompt(m, stage) + ' ' +
            'Produce a non-authoritative Thesys artifact proposal using only the supplied authoritative inputs, artifact index, human answers, clarification history and applicable human guidance. ' +
            'Human guidance is optional and non-authoritative: use it to orient the proposal, but never silently override an authoritative artifact or approved decision. If guidance conflicts with authoritative context, surface the conflict as a blocking question when it materially affects the current stage. ' +
            'Every artifact supplied under Authoritative artifacts is already human-approved and authoritative for this stage. ' +
            'Never ask whether an authoritative artifact, decision, requirement, clarification, or governance record is approved; its presence establishes authority. ' +
            self._language_rule(c.language) + ' ' +
            'The lifecycle below is authoritative for stage responsibilities and dependencies. For every question, apply the methodology question-blocking policy using the complete lifecycle, current stage, approved upstream artifacts, unit metadata and purpose of the decision. ' +
            'The model owns the semantic blocking decision; the runtime does not reinterpret it by topic, keyword or stage-specific heuristic. ' +
            'If blocking=false because a later stage owns the detail, explain that in why. If no material question remains, return an empty question list. ' +
            'Human answers are evidence that must be evaluated, not proof that the corresponding decision was resolved. ' +
            'For every previously blocking question in clarification history, if the answer resolves the decision materially, do not ask it again and incorporate the resulting decision without mentioning its question ID. If it does not resolve the decision, return a new blocking question without an ID. ' +
            'Questions are proposal metadata, never artifact content. Never place unresolved questions, pending decisions or their rationales in artifact sections. ' +
            'When referencing upstream artifacts, use the exact IDs and paths from the Artifact index. Do not invent, renumber or substitute artifact identifiers.'
        )
        inp = (
            f'Stage: {stage}\nUnit: {c.unit}\nScope: {c.unit_scope}\n'
            f'Authoritative Unit metadata:\n{json.dumps({"key":c.unit,"type":c.unit_type,"parent":c.unit_parent,"dependencies":list(c.unit_dependencies)}, ensure_ascii=False, indent=2)}\n\n'
            f'Authoritative artifacts:\n{json.dumps(c.approved_artifacts, ensure_ascii=False, indent=2)}\n\n'
            f'Artifact index (authoritative IDs and paths):\n{json.dumps(c.artifact_index, ensure_ascii=False, indent=2)}\n\n'
            f'Human answers:\n{json.dumps(c.answers, ensure_ascii=False, indent=2)}\n\n'
            f'Clarification history for this stage and unit:\n{json.dumps(c.clarification_history, ensure_ascii=False, indent=2)}\n\n'
            f'Human guidance applicable to this stage:\n{json.dumps(c.human_guidance, ensure_ascii=False, indent=2)}\n\n'
            f'Related Unit architecture inputs:\n{json.dumps(c.related_units, ensure_ascii=False, indent=2)}\n\n'
            f'Structural contract:\n{json.dumps(template_schema(m,stage), ensure_ascii=False, indent=2)}\n\n'
            f'Complete lifecycle contract:\n{json.dumps(_lifecycle_question_context(m, stage), ensure_ascii=False, indent=2)}'
        )
        return self._call(instructions, inp, schema, 'thesys_stage_proposal_structured')

    def propose_code(self, m, c):
        schema = {
            'type': 'object',
            'properties': {
                'files': {'type': 'array', 'items': {'type':'object','properties':{'path':{'type':'string'},'content':{'type':'string'}},'required':['path','content'],'additionalProperties':False}},
                'questions': {'type':'array','items': _question_schema()},
            },
            'required': ['files','questions'], 'additionalProperties': False,
        }
        rules=m.rules.get('implementation',{})
        allowed_roots=list(rules.get('allowed_roots',[]))
        allowed_root_files=list(rules.get('allowed_root_files',[]))
        instructions = (
            f'Generate a non-authoritative implementation proposal from approved engineering artifacts. Project language: {c.language}. '
            'Write human-readable comments and docstrings in the project language while preserving code syntax, identifiers, paths and API names. '
            f'Return only project-relative files under these allowed roots: {json.dumps(allowed_roots,ensure_ascii=False)}. '
            f'Root-level files are allowed only when explicitly listed here: {json.dumps(allowed_root_files,ensure_ascii=False)}. '
            'Never include secrets or claim that tests were executed.'
        )
        inp = f'Unit: {c.unit}\nScope: {c.unit_scope}\nAllowed roots: {json.dumps(allowed_roots,ensure_ascii=False)}\nAllowed root files: {json.dumps(allowed_root_files,ensure_ascii=False)}\nAuthoritative artifacts:\n{json.dumps(c.approved_artifacts,ensure_ascii=False,indent=2)}\nHuman answers:\n{json.dumps(c.answers,ensure_ascii=False,indent=2)}'
        return self._call(instructions, inp, schema, 'thesys_implementation_proposal')


def get_agent(name):
    if name == 'mock':
        return MockAgent()
    if name == 'openai':
        return OpenAIAgent()
    raise ThesysError(f'Unknown agent provider: {name}')
