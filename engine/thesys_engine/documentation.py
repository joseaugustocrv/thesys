import hashlib
import base64
import html
import json
import re
from pathlib import Path
from .io import read_text, write_text
from .registry import get
from .workflow import _load_answers
from .project import project_language


def _load_lifecycle():
    from .methodology import load_methodology
    bundle = Path(__file__).resolve().parent / "bundle"
    methodology = load_methodology(bundle)
    return [(stage.id, str(stage.config.get("artifact_prefix", stage.id.upper())), stage.name) for stage in methodology.stages]


LIFECYCLE = _load_lifecycle()
LIFECYCLE_TYPES = {code.upper() for _, code, _ in LIFECYCLE}


def _slug(value):
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    return value or "document"


def _inline(value):
    value = html.escape(value, quote=False)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", value)
    return value


def _split_table_row(line):
    """Split a Markdown table row while preserving escaped pipe characters."""
    value=line.strip()
    if value.startswith("|"):
        value=value[1:]
    if value.endswith("|") and not value.endswith("\\|"):
        value=value[:-1]
    cells=[]
    current=[]
    escaped=False
    for char in value:
        if escaped:
            if char == "|":
                current.append("|")
            else:
                current.extend(("\\", char))
            escaped=False
        elif char == "\\":
            escaped=True
        elif char == "|":
            cells.append("".join(current).strip())
            current=[]
        else:
            current.append(char)
    if escaped:
        current.append("\\")
    cells.append("".join(current).strip())
    return cells


def _table_separator(cell):
    return bool(re.fullmatch(r":?-{3,}:?", cell.strip()))


def _table_alignment(cell):
    cell=cell.strip()
    if cell.startswith(":") and cell.endswith(":"):
        return "center"
    if cell.endswith(":"):
        return "right"
    if cell.startswith(":"):
        return "left"
    return None


def _render_table(lines, start):
    headers=_split_table_row(lines[start])
    separators=_split_table_row(lines[start+1])
    if not headers or len(headers) != len(separators) or not all(_table_separator(x) for x in separators):
        return None, start
    rows=[]
    index=start+2
    while index < len(lines):
        line=lines[index]
        if not line.strip() or "|" not in line:
            break
        cells=_split_table_row(line)
        if len(cells) != len(headers):
            break
        rows.append(cells)
        index += 1
    alignments=[_table_alignment(x) for x in separators]
    out=['<div class="table-wrap"><table><thead><tr>']
    for i,cell in enumerate(headers):
        attr=f' style="text-align:{alignments[i]}"' if alignments[i] else ''
        out.append(f'<th scope="col"{attr}>{_inline(cell)}</th>')
    out.append('</tr></thead>')
    if rows:
        out.append('<tbody>')
        for row in rows:
            out.append('<tr>')
            for i,cell in enumerate(row):
                attr=f' style="text-align:{alignments[i]}"' if alignments[i] else ''
                out.append(f'<td{attr}>{_inline(cell)}</td>')
            out.append('</tr>')
        out.append('</tbody>')
    out.append('</table></div>')
    return "\n".join(out), index


def _markdown(text):
    lines = text.replace("\r\n", "\n").splitlines()
    out = []
    in_code = False
    code = []
    in_list = False
    index = 0
    while index < len(lines):
        line=lines[index]
        if line.strip().startswith("```"):
            if in_code:
                out.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
                code=[]
                in_code=False
            else:
                if in_list:
                    out.append("</ul>"); in_list=False
                in_code=True
            index += 1
            continue
        if in_code:
            code.append(line)
            index += 1
            continue
        if not line.strip():
            if in_list:
                out.append("</ul>"); in_list=False
            index += 1
            continue

        if "|" in line and index + 1 < len(lines) and "|" in lines[index+1]:
            rendered, next_index=_render_table(lines,index)
            if rendered is not None:
                if in_list:
                    out.append("</ul>"); in_list=False
                out.append(rendered)
                index=next_index
                continue

        if line.startswith("#"):
            if in_list:
                out.append("</ul>"); in_list=False
            m = re.match(r"^(#{1,6})\s+(.*)$", line)
            if m:
                level = len(m.group(1)); title = _inline(m.group(2)); anchor = _slug(re.sub(r"<[^>]+>", "", title))
                out.append(f'<h{level} id="{anchor}">{title}</h{level}>')
                index += 1
                continue
        m = re.match(r"^\s*[-*]\s+(.*)$", line)
        if m:
            if not in_list:
                out.append("<ul>"); in_list=True
            out.append(f"<li>{_inline(m.group(1))}</li>")
            index += 1
            continue
        m = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if m:
            if in_list:
                out.append("</ul>"); in_list=False
            out.append(f'<p class="ordered-item">{_inline(m.group(1))}</p>')
            index += 1
            continue
        if line.startswith(">"):
            if in_list:
                out.append("</ul>"); in_list=False
            out.append(f"<blockquote>{_inline(line[1:].lstrip())}</blockquote>")
            index += 1
            continue
        if in_list:
            out.append("</ul>"); in_list=False
        out.append(f"<p>{_inline(line)}</p>")
        index += 1
    if in_list: out.append("</ul>")
    if in_code: out.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
    return "\n".join(out)


def _evidence_value(value):
    if isinstance(value, list):
        return '<ul class="evidence-list">' + "".join(f"<li>{_inline(str(item))}</li>" for item in value) + '</ul>'
    if isinstance(value, dict):
        return '<pre class="evidence-json"><code>' + html.escape(json.dumps(value,ensure_ascii=False,indent=2)) + '</code></pre>'
    if value is None:
        return '<span class="muted">—</span>'
    return _inline(str(value))


def _evidence_html(content):
    try:
        data=json.loads(content)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(data,dict):
        return None
    rows=[]
    for key,value in data.items():
        label=key.replace("_"," ").strip().title()
        rows.append(f'<tr><th scope="row">{_inline(label)}</th><td>{_evidence_value(value)}</td></tr>')
    return '<div class="evidence-card"><table><tbody>' + "\n".join(rows) + '</tbody></table></div>'


def _artifact_stage(project, path, unit, methodology=None):
    """Resolve the lifecycle stage from the authoritative methodology path."""
    if methodology is None:
        from .methodology import load_methodology
        bundle = Path(__file__).resolve().parent / "bundle"
        methodology = load_methodology(bundle)
    relative = path.resolve()
    for stage in methodology.stages:
        target = methodology.artifact_path(project, stage, unit if stage.config.get("scope") != "project" else "default")
        if target and target.resolve() == relative:
            return stage.id
    return None


def _artifact_items(project):
    data = get(project)
    items = []
    for aid, item in data.get("artifacts", {}).items():
        path = Path(item.get("path", ""))
        if not path.is_absolute(): path = project / path
        if not path.is_file(): continue
        try:
            content = read_text(path)
        except OSError:
            continue
        unit = item.get("unit", "default")
        stage = _artifact_stage(project, path, unit)
        items.append({
            "id": aid,
            "type": item.get("type", "artifact"),
            "stage": stage,
            "unit": unit,
            "status": item.get("status", ""),
            "authority": item.get("authority", ""),
            "path": str(path.relative_to(project)).replace("\\", "/"),
            "title": _title(content, aid),
            "content": content,
        })
    return items


def _title(content, fallback):
    for line in content.splitlines():
        m = re.match(r"^#\s+(.+)$", line.strip())
        if m: return m.group(1).strip()
    return fallback


def _proposals(project):
    result = {}
    root = project / ".thesys" / "proposals"
    if not root.is_dir(): return result
    for path in root.glob("*/*.json"):
        try:
            data = json.loads(read_text(path))
        except (OSError, json.JSONDecodeError):
            continue
        key = f"{data.get('stage')}:{data.get('unit', path.parent.name)}"
        result[key] = data
    return result


def _proposal_items(project):
    """Expose current non-authoritative proposals in the documentation site."""
    result = []
    root = project / ".thesys" / "proposals"
    if not root.is_dir():
        return result
    try:
        approvals = json.loads(read_text(project / ".thesys" / "approvals.json")).get("approvals", {})
    except (OSError, json.JSONDecodeError):
        approvals = {}
    for path in sorted(root.glob("*/*.json")):
        try:
            data = json.loads(read_text(path))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("status") == "accepted":
            continue
        stage = data.get("stage", path.stem)
        unit = data.get("unit", path.parent.name)
        approval = approvals.get(f"{stage}:{unit}")
        if approval and approval.get("proposal_id") == data.get("proposal_id") and data.get("status") != "needs_regeneration":
            continue
        code = next((code for key, code, _ in LIFECYCLE if key == stage), stage.upper())
        content = data.get("content", "")
        if stage == "intent":
            try:
                body = json.loads(content)
                content = (body.get("intent", "") + "\n\n---\n\n" + body.get("context", "")).strip()
            except (TypeError, json.JSONDecodeError):
                pass
        if data.get("status") == "needs_regeneration":
            state = "stale"
        elif any(q.get("blocking", True) for q in data.get("questions", [])):
            state = "blocked"
        else:
            state = "proposed"
        result.append({
            "id": data.get("proposal_id", f"PROP:{stage}:{unit}"),
            "type": code,
            "unit": unit,
            "status": state,
            "authority": "non-authoritative",
            "path": str(path.relative_to(project)).replace("\\", "/"),
            "title": f"Proposta · {stage} · {unit}",
            "content": content,
            "proposal": True,
            "stage": stage,
            "questions": data.get("questions", []),
            "clarification_history": data.get("clarification_history", []),
        })
    return result

def _approval_state(project, item):
    language = project_language(project, "en-US")
    pt = language.lower().startswith("pt-")
    labels = {
        "stale": "Proposta desatualizada · regeneração necessária" if pt else "Proposal stale · regeneration required",
        "blocked": "Proposta bloqueada · esclarecimento necessário" if pt else "Proposal blocked · clarification required",
        "proposed": "Proposta · não autoritativa · aprovação humana necessária" if pt else "Proposal · non-authoritative · human approval required",
        "not-approved": "Não aprovado" if pt else "Not approved",
        "approval-unverified": "Aprovação registrada; fonte indisponível" if pt else "Approval recorded; source unavailable",
        "approval-stale": "Aprovação desatualizada" if pt else "Approval stale",
        "approved": "Aprovado · autoritativo" if pt else "Approved · authoritative",
    }
    if item.get("proposal"):
        if item.get("status") == "stale":
            return {"state": "stale", "label": labels["stale"], "approved_at": None}
        if item.get("status") == "blocked":
            return {"state": "blocked", "label": labels["blocked"], "approved_at": None}
        return {"state": "proposed", "label": labels["proposed"], "approved_at": None}
    approvals_path = project / ".thesys" / "approvals.json"
    try:
        approvals = json.loads(read_text(approvals_path)).get("approvals", {})
    except (OSError, json.JSONDecodeError):
        approvals = {}
    stage = item.get("stage") or next((key for key, code, _ in LIFECYCLE if code == item["type"]), item["type"].lower())
    approval = approvals.get(f"{stage}:{item['unit']}")
    if not approval:
        return {"state": "not-approved", "label": labels["not-approved"], "approved_at": None}
    path = project / item["path"]
    try:
        current_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return {"state": "approval-unverified", "label": labels["approval-unverified"], "approved_at": approval.get("approved_at")}
    if current_sha != approval.get("sha256"):
        return {"state": "approval-stale", "label": labels["approval-stale"], "approved_at": approval.get("approved_at")}
    return {"state": "approved", "label": labels["approved"], "approved_at": approval.get("approved_at")}

def _display_content(item, approval):
    """Render stored artifact content without injecting lifecycle metadata."""
    return item["content"]


def _related(project, item, artifacts, proposals, answers):
    registry = get(project)
    relations = registry.get("relations", [])
    ids = {item["id"]}
    for relation in relations:
        if relation.get("source") == item["id"]: ids.add(relation.get("target"))
        if relation.get("target") == item["id"]: ids.add(relation.get("source"))
    referenced = set(re.findall(r"\b(?:INT|CTX|GOV|REQ|CLR|SPE|ACC|ARC|QRE|SEC|RSK|PLN|TSK|VER|CON|REL|OPS|CHG|RET|EVD|PRJ|[A-Z]{2,5})-[0-9A-Z]+\b", item["content"]))
    artifact_by_id = {x["id"]: x for x in artifacts}
    for ref in referenced:
        if ref in artifact_by_id: ids.add(ref)
    related = [artifact_by_id[x] for x in ids if x in artifact_by_id and x != item["id"]]
    related.sort(key=lambda x: (x["type"], x["id"]))
    stage = item.get("stage") or next((key for key, code, _ in LIFECYCLE if code == item["type"]), item["type"].lower())
    proposal = proposals.get(f"{stage}:{item['unit']}") or proposals.get(f"{stage}:default")
    questions = []
    # Keep both current proposal questions and the durable clarification history.
    # Regeneration may remove answered questions from the current proposal, but
    # the human answer remains part of the project's traceable decision record.
    history = []
    for qid, record in answers.items():
        if not isinstance(record, dict):
            continue
        if record.get("stage") == stage and record.get("unit") == item.get("unit"):
            history.append({"id": qid, **record, "answer": record.get("answer")})
    seen = set()
    for q in history:
        seen.add(q.get("id")); questions.append(q)
    if proposal:
        for q in proposal.get("questions", []):
            if q.get("id") in seen:
                continue
            q = dict(q)
            q["answer"] = answers.get(q.get("id"), {}).get("answer")
            questions.append(q)
    return related, questions


_DOC_UI = {
    "en-US": {
        "documentation": "DOCUMENTATION", "search": "Search artifacts…", "copy": "Copy link",
        "project_documentation": "Project documentation", "references": "References", "approval": "Approval",
        "related": "Related artifacts", "questions": "Questions & answers", "history": "Clarification history",
        "metadata": "Metadata", "supporting": "Supporting artifacts", "lifecycle": "Lifecycle",
        "approved": "approved", "upcoming": "Upcoming", "not_generated": "Not generated",
        "authoritative": "authoritative", "upcoming_count": "upcoming", "no_related": "No related artifacts found.",
        "no_questions": "No proposal questions for this artifact.", "unanswered": "Unanswered", "answer": "Answer",
        "technical": "Technical details", "path": "Path", "state": "Project state", "registry": "Registry status",
        "authority": "Authority", "unit": "Unit", "no_history": "No answered questions for this artifact.",
        "proposal": "Proposal ·", "proposal_review": "Proposal · non-authoritative · human approval required",
    },
    "pt-BR": {
        "documentation": "DOCUMENTAÇÃO", "search": "Pesquisar artefatos…", "copy": "Copiar link",
        "project_documentation": "Documentação do projeto", "references": "Referências", "approval": "Aprovação",
        "related": "Artefatos relacionados", "questions": "Perguntas e respostas", "history": "Histórico de esclarecimentos",
        "metadata": "Metadados", "supporting": "Artefatos de apoio", "lifecycle": "Ciclo de vida",
        "approved": "aprovado", "upcoming": "Próxima etapa", "not_generated": "Não gerado",
        "authoritative": "autoritativo", "upcoming_count": "próximas", "no_related": "Nenhum artefato relacionado encontrado.",
        "no_questions": "Nenhuma pergunta da proposta para este artefato.", "unanswered": "Sem resposta", "answer": "Resposta",
        "technical": "Detalhes técnicos", "path": "Caminho", "state": "Estado do projeto", "registry": "Status do registro",
        "authority": "Autoridade", "unit": "Unidade", "no_history": "Nenhuma pergunta respondida para este artefato.",
        "proposal": "Proposta ·", "proposal_review": "Proposta · não autoritativa · aprovação humana necessária",
    },
}

def _site_html(project, items, proposals, answers):
    payload = []
    for item in items:
        related, questions = _related(project, item, items, proposals, answers)
        approval = _approval_state(project, item)
        payload.append({
            **{k: item[k] for k in ("id", "type", "stage", "unit", "status", "authority", "path", "title")},
            "proposal": bool(item.get("proposal")),
            "stage": item.get("stage"),
            "clarification_history": item.get("clarification_history", []),
            "html": (_evidence_html(item["content"]) if item["type"].upper() == "EVD" else None) or _markdown(_display_content(item, approval)),
            "related": [x["id"] for x in related],
            "questions": questions,
            "approval": approval,
        })
    payload.sort(key=lambda x: _nav_key(x))
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    question_history = json.dumps([dict({"id": qid}, **record) for qid, record in answers.items() if isinstance(record, dict) and record.get("answer")], ensure_ascii=False).replace("</", "<\\/")
    language = project_language(project, "en-US")
    localization_path = Path(__file__).resolve().parent / "bundle" / "methodology" / "localization" / f"{language}.json"
    try:
        localization = json.loads(read_text(localization_path))
    except (OSError, json.JSONDecodeError):
        localization = {}
    titles = localization.get("titles", {})
    lifecycle = json.dumps([(key, code, titles.get(name, name).replace("[Unit key]", "{unit}")) for key, code, name in LIFECYCLE], ensure_ascii=False)
    from .methodology import load_methodology
    bundle = Path(__file__).resolve().parent / "bundle"
    method = load_methodology(bundle)
    lifecycle_scopes = {
        stage.id: str(stage.config.get("scope", "unit"))
        for stage in method.stages
    }
    lifecycle_scope_json = json.dumps(lifecycle_scopes, ensure_ascii=False)
    unit_keys = sorted({str(x.get("unit")) for x in items if x.get("unit") and x.get("unit") != "default"})
    unit_keys_json = json.dumps(unit_keys, ensure_ascii=False)
    project_name = project.name
    ui = _DOC_UI.get(language, _DOC_UI["en-US"])
    logo_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 128">'
        '<rect width="128" height="128" rx="24" fill="#0F766E"/>'
        '<path d="M24 64h32l16-28 16 28-16 28-16-28H24zm48 0h32" fill="none" stroke="#fff" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>'
        '<text x="152" y="82" font-family="Arial,sans-serif" font-size="58" font-weight="700" fill="#182433">THESYS</text>'
        '</svg>'
    )
    logo_svg = base64.b64encode(logo_svg.encode("utf-8")).decode("ascii")
    return (_HTML.replace("__DATA__", data)
                  .replace("__QUESTION_HISTORY__", question_history)
                  .replace("__LIFECYCLE__", lifecycle)
                  .replace("__LIFECYCLE_SCOPES__", lifecycle_scope_json)
                  .replace("__UNIT_KEYS__", unit_keys_json)
                  .replace("__PROJECT__", html.escape(project_name))
                  .replace("__LANG__", html.escape(language))
                  .replace("__LOGO_SVG__", logo_svg)
                  .replace("__UI_DOCUMENTATION__", ui["documentation"])
                  .replace("__UI_SEARCH__", ui["search"])
                  .replace("__UI_COPY__", ui["copy"])
                  .replace("__UI_PROJECT_DOCUMENTATION__", ui["project_documentation"])
                  .replace("__UI_REFERENCES__", ui["references"])
                  .replace("__UI_RELATED__", ui["related"])
                  .replace("__UI_QUESTIONS__", ui["questions"])
                  .replace("__UI_HISTORY__", ui["history"])
                  .replace("__UI_METADATA__", ui["metadata"])
                  .replace("__UI_UPCOMING__", ui["upcoming"])
                  .replace("__UI_NOT_GENERATED__", ui["not_generated"])
                  .replace("__UI_APPROVED__", ui["approved"])
                  .replace("__UI_SUPPORTING__", ui["supporting"])
                  .replace("__UI_LIFECYCLE__", ui["lifecycle"])
                  .replace("__UI_PROPOSAL__", ui["proposal"])
                  .replace("__UI_NO_RELATED__", ui["no_related"])
                  .replace("__UI_NO_QUESTIONS__", ui["no_questions"])
                  .replace("__UI_UNANSWERED__", ui["unanswered"])
                  .replace("__UI_ANSWER__", ui["answer"])
                  .replace("__UI_NO_HISTORY__", ui["no_history"])
                  .replace("__UI_STATE__", ui["state"])
                  .replace("__UI_REGISTRY__", ui["registry"])
                  .replace("__UI_AUTHORITY__", ui["authority"])
                  .replace("__UI_UNIT__", ui["unit"])
                  .replace("__UI_TECHNICAL__", ui["technical"])
                  .replace("__UI_PATH__", ui["path"]) )


def _nav_key(item):
    stage = item.get("stage")
    if stage:
        order = next((i for i, (key, _, _) in enumerate(LIFECYCLE) if key == stage), len(LIFECYCLE))
        return (0, order, item["unit"], item["id"])
    t = item["type"].upper()
    if t in LIFECYCLE_TYPES:
        order = next(i for i, (_, code, _) in enumerate(LIFECYCLE) if code.upper() == t)
        return (0, order, item["unit"], item["id"])
    return (1, item["type"], item["unit"], item["id"])


_HTML = r'''<!doctype html>
<html lang="__LANG__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Thesys — __PROJECT__ Documentation</title>
<link rel="stylesheet" href="styles.css">
</head>
<body>
<header class="global-header">
  <div class="header-brand"><img src="data:image/svg+xml;base64,__LOGO_SVG__" alt="Thesys logo"></div>
  <div class="header-project"><span>__UI_DOCUMENTATION__</span><strong>__PROJECT__</strong></div>
  <div class="header-actions"><button id="toggle-left" type="button" aria-label="Toggle navigation">☰</button><button id="toggle-right" type="button" aria-label="Toggle references">☷</button></div>
</header>
<div class="app">
  <aside class="sidebar">
    <div class="panel-head"><strong>__UI_LIFECYCLE__</strong><button id="collapse-left" type="button" aria-label="Collapse navigation">‹</button></div>
    <div class="brand"><span>__UI_DOCUMENTATION__</span></div>
    <div id="progress" class="progress"></div>
    <input id="search" type="search" placeholder="__UI_SEARCH__" aria-label="__UI_SEARCH__">
    <div id="nav" class="nav"></div>
  </aside>
  <main class="content">
    <header class="topbar"><div id="crumb">__UI_PROJECT_DOCUMENTATION__</div><button id="copy-link">__UI_COPY__</button></header>
    <article id="document" class="document"></article>
  </main>
  <aside class="related">
    <div class="panel-head"><strong>__UI_REFERENCES__</strong><button id="collapse-right" type="button" aria-label="Collapse references">›</button></div>
    <section id="approval-panel"></section>
    <section><h3>__UI_RELATED__</h3><div id="related-artifacts"></div></section>
    <section><h3>__UI_QUESTIONS__</h3><div id="questions"></div></section><section><h3>__UI_HISTORY__</h3><div id="history"></div></section>
    <section><h3>__UI_METADATA__</h3><dl id="metadata"></dl></section>
  </aside>
</div>
<script>
const DATA = __DATA__;
const LIFECYCLE = __LIFECYCLE__;
const LIFECYCLE_SCOPES = __LIFECYCLE_SCOPES__;
const UNIT_KEYS = __UNIT_KEYS__;
const byId = Object.fromEntries(DATA.map(x => [x.id, x]));
const nav = document.getElementById('nav');
const doc = document.getElementById('document');
const related = document.getElementById('related-artifacts');
const questions = document.getElementById('questions');
const history = document.getElementById('history');
const QUESTION_HISTORY = __QUESTION_HISTORY__;
const metadata = document.getElementById('metadata');
const approvalPanel = document.getElementById('approval-panel');
const progress = document.getElementById('progress');
const search = document.getElementById('search');
const app = document.querySelector('.app');
function setPanelState(side, collapsed){ app.classList.toggle(side === 'left' ? 'left-collapsed' : 'right-collapsed', collapsed); localStorage.setItem('thesys-doc-' + side, collapsed ? 'collapsed' : 'open'); }
function bindPanelToggles(){
  const leftCollapsed = localStorage.getItem('thesys-doc-left') === 'collapsed';
  const rightCollapsed = localStorage.getItem('thesys-doc-right') === 'collapsed';
  setPanelState('left', leftCollapsed); setPanelState('right', rightCollapsed);
  document.getElementById('collapse-left').onclick=()=>setPanelState('left', !app.classList.contains('left-collapsed'));
  document.getElementById('collapse-right').onclick=()=>setPanelState('right', !app.classList.contains('right-collapsed'));
  document.getElementById('toggle-left').onclick=()=>setPanelState('left', !app.classList.contains('left-collapsed'));
  document.getElementById('toggle-right').onclick=()=>setPanelState('right', !app.classList.contains('right-collapsed'));
}

let current = null;
function esc(s){ const d=document.createElement('div'); d.textContent=s ?? ''; return d.innerHTML; }
function stageItems(stageKey){ return DATA.filter(x => x.stage && x.stage.toLowerCase()===stageKey.toLowerCase()); }
function expectedUnits(stageKey){ return (LIFECYCLE_SCOPES[stageKey]||'unit')==='project' ? ['default'] : UNIT_KEYS; }
function stageState(index){
  const [key,code]=LIFECYCLE[index];
  const existing=stageItems(key);
  const expected=expectedUnits(key);
  const authoritative=existing.filter(x=>!x.proposal);
  const approved=authoritative.filter(x=>x.approval?.state==='approved');
  if(expected.length && approved.length===expected.length && expected.every(u=>approved.some(x=>x.unit===u))) return 'approved';
  if(existing.some(x=>x.proposal)) return existing.some(x=>x.proposal && x.status==='blocked') ? 'blocked' : 'review';
  if(authoritative.length) return approved.length ? 'partial' : 'documented';
  const lastGenerated=LIFECYCLE.reduce((last,_,i)=>stageItems(LIFECYCLE[i][0]).length ? i : last,-1);
  return index>lastGenerated ? 'upcoming' : 'not-generated';
}
function itemState(x){ if(!x.proposal && x.approval?.state==='approved') return 'approved'; if(x.proposal && x.status==='blocked') return 'blocked'; if(x.proposal) return 'review'; return 'documented'; }
function renderNav(filter=''){
  const q=filter.trim().toLowerCase();
  const lifecycleHtml = LIFECYCLE.map(([key,code,label],index) => {
    const existing=stageItems(key);
    const xs=existing.filter(x => !q || (`${x.id} ${x.title} ${x.path} ${x.html}`).toLowerCase().includes(q));
    if(q && !xs.length) return '';
    const state=stageState(index);
    if(!existing.length){
      const labelText=state==='upcoming'?'__UI_UPCOMING__':'__UI_NOT_GENERATED__';
      return `<div class="nav-stage ${state}"><span class="stage-dot"></span><div><strong>${esc(label)}</strong><small>${labelText}</small></div></div>`;
    }
    const count=xs.length;
    const approvedCount=xs.filter(x=>!x.proposal && x.approval?.state==='approved').length;
    const children=xs.sort((a,b)=>a.id.localeCompare(b.id)).map(x=>`<button class="nav-item ${x.proposal?'proposal-item':''}" data-id="${esc(x.id)}"><span><i class="item-dot ${itemState(x)}"></i>${esc(x.proposal?'Proposta · ':'')}${esc(label)} · ${esc(x.id)}</span><small>${esc(x.title)}</small></button>`).join('');
    return `<details class="nav-phase" data-stage="${esc(code)}"${q?' open':''}><summary class="nav-stage ${state}"><span class="stage-dot"></span><div><strong>${esc(label)}</strong><small>${approvedCount}/${count} approved</small></div></summary><div class="nav-phase-items">${children}</div></details>`;
  }).join('');
  const supportTypes=[...new Set(DATA.map(x=>x.type).filter(t=>!LIFECYCLE.some(([,code])=>code.toUpperCase()===t.toUpperCase())))].sort();
  const supportHtml=supportTypes.map(type=>{
    const xs=DATA.filter(x=>x.type===type && (!q || (`${x.id} ${x.title} ${x.path} ${x.html}`).toLowerCase().includes(q)));
    if(!xs.length) return '';
    return `<div class="nav-group"><div class="nav-title">${esc(type)}</div>${xs.sort((a,b)=>a.id.localeCompare(b.id)).map(x=>`<button class="nav-item" data-id="${esc(x.id)}"><span><i class="item-dot ${itemState(x)}"></i>${esc(x.id)}</span><small>${esc(x.title)}</small></button>`).join('')}</div>`;
  }).join('');
  nav.innerHTML=`<div class="nav-section"><div class="nav-title">Lifecycle</div>${lifecycleHtml}</div>${supportHtml?`<div class="nav-section support"><div class="nav-title">Supporting artifacts</div>${supportHtml}</div>`:''}`;
  nav.querySelectorAll('[data-id]').forEach(b=>b.onclick=()=>select(b.dataset.id));
}
function renderProgress(){
  const total=LIFECYCLE.length;
  const generated=LIFECYCLE.filter(([key])=>stageItems(key).some(x=>!x.proposal)).length;
  const approved=LIFECYCLE.filter(([key],index)=>stageState(index)==='approved').length;
  const upcoming=LIFECYCLE.filter(([key],index)=>!stageItems(key).length && stageState(index)==='upcoming').length;
  const percentage=total ? Math.round((generated/total)*100) : 0;
  progress.innerHTML=`<div class="progress-label"><strong>${generated}/${total}</strong> lifecycle stages documented</div><div class="progress-bar"><span style="width:${percentage}%"></span></div><small>${approved} authoritative · ${upcoming} upcoming</small>`;
}
function select(id, push=true){
  const x=byId[id]; if(!x) return;
  current=x;
  doc.innerHTML=x.html;
  document.getElementById('crumb').textContent=`${x.id} · ${x.title}`;
  approvalPanel.innerHTML=`<div class="approval ${esc(x.approval?.state||'not-approved')}"><strong>${esc(x.approval?.label||'Approval state unavailable')}</strong>${x.approval?.approved_at?`<small>Approved ${esc(new Date(x.approval.approved_at).toLocaleString())}</small>`:''}</div>`;
  related.innerHTML=(x.related||[]).map(id=>{const r=byId[id]; return r?`<button class="ref" data-id="${esc(id)}"><strong>${esc(id)}</strong><span>${esc(r.title)}</span></button>`:''}).join('') || '<p class="muted">__UI_NO_RELATED__</p>';
  related.querySelectorAll('[data-id]').forEach(b=>b.onclick=()=>select(b.dataset.id));
  questions.innerHTML=(x.questions||[]).map(q=>`<div class="question"><strong>${esc(q.id)}</strong><p>${esc(q.question)}</p><span class="badge ${q.blocking?'blocking':'nonblocking'}">${q.blocking?'blocking':'non-blocking'}</span>${q.answer?`<div class="answer"><b>__UI_ANSWER__</b><p>${esc(q.answer)}</p></div>`:'<div class="muted">__UI_UNANSWERED__</div>'}</div>`).join('') || '<p class="muted">__UI_NO_QUESTIONS__</p>';
  const itemHistory=(x.clarification_history||QUESTION_HISTORY||[]).filter(q=>q.stage===((x.stage||((x.type||'').toLowerCase()==='int'?'intent':((LIFECYCLE.find(([key,code])=>code.toLowerCase()===(x.type||'').toLowerCase())||[])[0]||'')))) && q.unit===x.unit);
  history.innerHTML=itemHistory.map(q=>`<div class="question"><strong>${esc(q.id)}</strong><p>${esc(q.question)}</p><span class="badge ${q.blocking?'blocking':'nonblocking'}">${q.blocking?'blocking':'non-blocking'}</span><div class="answer"><b>__UI_ANSWER__</b><p>${esc(q.answer)}</p></div></div>`).join('') || '<p class="muted">__UI_NO_HISTORY__</p>';
  metadata.innerHTML=`<dt>__UI_STATE__</dt><dd>${esc(x.approval?.label||'Unknown')}</dd><dt>__UI_REGISTRY__</dt><dd>${esc(x.status)}</dd><dt>__UI_AUTHORITY__</dt><dd>${esc(x.authority)}</dd><dt>__UI_UNIT__</dt><dd>${esc(x.unit)}</dd><details class="technical-details"><summary>Technical details</summary><dt>__UI_PATH__</dt><dd><code>${esc(x.path)}</code></dd></details>`;
  document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.id===id));
  const selectedButton=document.querySelector(`.nav-item[data-id="${CSS.escape(id)}"]`);
  const phase=selectedButton?.closest('.nav-phase');
  if(phase) phase.open=true;
  if(push) history.replaceState(null,'',`#${encodeURIComponent(id)}`);
}
search.oninput=()=>renderNav(search.value);
document.getElementById('copy-link').onclick=()=>navigator.clipboard?.writeText(location.href);
bindPanelToggles();
renderProgress();
renderNav();
const initial=decodeURIComponent(location.hash.slice(1));
const first=LIFECYCLE.flatMap(([key])=>stageItems(key)).find(Boolean)?.id || DATA[0]?.id;
select(byId[initial]?initial:first,false);
</script>
</body>
</html>'''

_CSS = r''' :root{color-scheme:light;--border:#e2e5e9;--muted:#68717c;--bg:#f6f7f9;--panel:#fff;--accent:#24292f;--ok:#176b3a;--okbg:#e8f5ed}*{box-sizing:border-box}html,body{height:100%;margin:0}body{font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;color:#20252b;background:var(--bg);display:flex;flex-direction:column}button,input{font:inherit}.global-header{height:64px;flex:0 0 64px;display:flex;align-items:center;gap:18px;padding:0 22px;background:#fff;border-bottom:1px solid var(--border);z-index:20}.header-brand img{display:block;width:118px;height:auto}.header-project{display:flex;flex-direction:column;line-height:1.15}.header-project span{font-size:9px;color:var(--muted);font-weight:700;letter-spacing:.14em}.header-project strong{font-size:14px;font-weight:700;margin-top:3px}.header-actions{margin-left:auto;display:flex;gap:6px}.header-actions button,.panel-head button{width:30px;height:30px;border:1px solid var(--border);border-radius:7px;background:#fff;color:#4b535b;cursor:pointer}.header-actions button:hover,.panel-head button:hover,.topbar button:hover{background:#f0f2f4}.app{display:grid;grid-template-columns:300px minmax(0,1fr) 300px;min-height:0;flex:1;transition:grid-template-columns .18s ease}.app.left-collapsed{grid-template-columns:0 minmax(0,1fr) 300px}.app.right-collapsed{grid-template-columns:300px minmax(0,1fr) 0}.app.left-collapsed.right-collapsed{grid-template-columns:0 minmax(0,1fr) 0}.sidebar,.related{background:var(--panel);overflow:auto;min-width:0}.sidebar{border-right:1px solid var(--border);padding:16px}.related{border-left:1px solid var(--border);padding:16px}.left-collapsed .sidebar,.right-collapsed .related{padding:0;overflow:hidden;border:0}.panel-head{height:32px;display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}.brand{text-align:center;font-weight:800;letter-spacing:.08em;margin-bottom:8px}.brand span{font-size:9px;color:var(--muted);font-weight:700;display:block;letter-spacing:.14em}.progress{padding:8px 0 14px;border-bottom:1px solid var(--border);margin-bottom:14px}.progress-label{font-size:12px;color:#343a40}.progress-label strong{font-size:14px}.progress small{display:block;color:var(--muted);margin-top:5px}.progress-bar{height:5px;background:#edf0f2;border-radius:5px;overflow:hidden;margin-top:7px}.progress-bar span{display:block;height:100%;background:#20252b;border-radius:5px}#search{width:100%;padding:9px 10px;border:1px solid var(--border);border-radius:7px;margin-bottom:16px}.nav-section{margin:0 0 20px}.nav-title{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:700;margin:0 0 5px}.nav-phase{margin:0 0 3px;border-radius:7px}.nav-phase>summary{list-style:none;cursor:pointer}.nav-phase>summary::-webkit-details-marker{display:none}.nav-phase>summary:after{content:"›";margin-left:auto;font-size:16px;color:var(--muted);transform:rotate(0deg);transition:transform .12s ease}.nav-phase[open]>summary:after{transform:rotate(90deg)}.nav-stage{display:flex;gap:8px;align-items:center;padding:7px 8px;color:#343a40}.nav-stage.upcoming{opacity:.72}.nav-stage.not-generated{opacity:.62}.nav-stage.approved{color:#20252b}.nav-stage.approved strong{color:#20252b}.nav-stage.approved small{color:#68717c}.nav-stage strong{display:block;font-size:12px}.nav-stage small{display:block;color:var(--muted);font-size:11px;margin-top:2px}.stage-dot{width:8px;height:8px;border-radius:50%;background:#b9c0c7;flex:0 0 auto}.nav-stage.upcoming .stage-dot{background:#8f969d}.nav-stage.approved .stage-dot{background:var(--ok);box-shadow:0 0 0 2px var(--okbg)}.nav-stage.partial .stage-dot,.nav-stage.review .stage-dot{background:#c58b00}.nav-stage.blocked .stage-dot{background:#b23a3a}.item-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#b9c0c7;margin-right:6px}.item-dot.approved{background:var(--ok)}.item-dot.review{background:#c58b00}.item-dot.blocked{background:#b23a3a}.item-dot.documented{background:#8f969d}.nav-phase-items{padding:0 0 5px 15px}.nav-item,.ref{width:100%;text-align:left;background:none;border:0;border-radius:6px;padding:8px;cursor:pointer}.nav-item:hover,.nav-item.active,.ref:hover{background:#f0f2f4}.nav-item span{display:block;font-size:12px;font-weight:700}.nav-item small,.ref span{display:block;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px}.support{padding-top:4px;border-top:1px solid var(--border)}.content{overflow:auto;background:#fff;min-width:0}.topbar{position:sticky;top:0;background:rgba(255,255,255,.94);backdrop-filter:blur(8px);border-bottom:1px solid var(--border);height:52px;padding:0 32px;display:flex;align-items:center;justify-content:space-between;color:var(--muted);font-size:13px;z-index:5}.topbar button{border:1px solid var(--border);background:#fff;border-radius:6px;padding:6px 10px;cursor:pointer}.document{max-width:900px;margin:0 auto;padding:42px 52px 80px}.document h1,.document h2,.document h3{scroll-margin-top:80px}.document h1{font-size:32px}.document h2{margin-top:34px;border-bottom:1px solid var(--border);padding-bottom:8px}.document p,.document li{line-height:1.65}.table-wrap{overflow-x:auto;margin:18px 0 24px}.document table,.evidence-card table{width:100%;border-collapse:collapse;font-size:13px}.document th,.document td,.evidence-card th,.evidence-card td{border:1px solid var(--border);padding:9px 10px;vertical-align:top;text-align:left}.document th,.evidence-card th{background:#f7f8f9;font-weight:700}.document tbody tr:nth-child(even),.evidence-card tbody tr:nth-child(even){background:#fcfcfd}.evidence-card{margin:18px 0 24px}.evidence-list{margin:0;padding-left:18px}.evidence-json{margin:0}.technical-details{grid-column:1/-1;margin-top:5px}.technical-details summary{cursor:pointer;color:var(--muted);font-size:12px}.technical-details dt{margin-top:8px}.technical-details dd{margin-bottom:0}.document pre{background:#f3f4f6;padding:14px;border-radius:8px;overflow:auto}.document code{background:#f1f2f3;padding:2px 4px;border-radius:4px}.document pre code{background:none;padding:0}.document blockquote{border-left:3px solid #ccd1d6;padding-left:14px;color:var(--muted)}.related h2{margin:0 0 18px}.related h3{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}.related section{margin-bottom:24px}.approval{padding:11px 12px;border-radius:8px;background:#f3f4f6;border:1px solid var(--border)}.approval.approved{background:var(--okbg);border-color:#c9e5d5;color:var(--ok)}.approval small{display:block;margin-top:4px;color:var(--muted);font-size:11px}.ref{border-bottom:1px solid var(--border);padding:9px 2px}.ref strong{display:block}.question{border-bottom:1px solid var(--border);padding:10px 0}.question p{font-size:13px;line-height:1.45}.badge{font-size:10px;text-transform:uppercase;letter-spacing:.06em;padding:3px 6px;border-radius:10px;background:#eef0f2}.blocking{background:#f5dddd}.nonblocking{background:#e6f1e7}.answer{margin-top:10px;padding:9px;background:#f7f8f9;border-radius:6px}.answer p{margin-bottom:0}.muted{color:var(--muted);font-size:13px}.related dl{display:grid;grid-template-columns:92px 1fr;gap:7px;font-size:12px}.related dt{color:var(--muted)}.related dd{margin:0;overflow-wrap:anywhere}@media(max-width:1100px){.app{grid-template-columns:260px minmax(0,1fr)}.related{display:none}.app.left-collapsed{grid-template-columns:0 minmax(0,1fr)}.app.right-collapsed{grid-template-columns:260px minmax(0,1fr)}}@media(max-width:700px){.global-header{height:56px;flex-basis:56px;padding:0 14px}.header-brand img{width:100px}.app,.app.left-collapsed,.app.right-collapsed,.app.left-collapsed.right-collapsed{display:block}.sidebar{height:auto;max-height:40vh;border-right:0;border-bottom:1px solid var(--border)}.content{height:60vh}.document{padding:28px 20px 50px}.topbar{padding:0 18px}}'''


def build_documentation(project, output=None, open_browser=False):
    project = Path(project).resolve()
    if not (project / ".thesys").is_dir():
        raise ValueError(f"Not a Thesys project: {project}")
    output = Path(output).resolve() if output else project / ".thesys" / "docs"
    output.mkdir(parents=True, exist_ok=True)
    items = _artifact_items(project)
    items.extend(_proposal_items(project))
    # Once child Engineering Units exist, `default` is a container rather than
    # an engineering Unit. Hide stale unit-scoped default artifacts from the
    # documentation projection; project-scoped Governance remains visible.
    unit_files = list((project / ".thesys" / "units").glob("*.json"))
    has_child_units = any(p.stem != "default" for p in unit_files)
    if has_child_units:
        # `default` becomes a container for Unit-scoped lifecycle stages, but
        # project-scoped authoritative artifacts (Intent, Governance and other
        # project-scoped stages) remain part of the lifecycle record.
        from .methodology import load_methodology
        bundle = Path(__file__).resolve().parent / "bundle"
        method = load_methodology(bundle)
        project_scoped_codes = {
            str(stage.config.get("artifact_prefix", stage.id.upper())).upper()
            for stage in method.stages
            if stage.config.get("scope") == "project"
        }
        items = [
            x for x in items
            if x.get("proposal")
            or x.get("unit") != "default"
            or x.get("type", "").upper() in project_scoped_codes
        ]
    proposals = _proposals(project)
    answers = _load_answers(project)
    write_text(output / "index.html", _site_html(project, items, proposals, answers))
    write_text(output / "styles.css", _CSS)
    manifest = {"schema":"1","generated_by":"thesys docs build","artifact_count":len(items),"artifacts":[{"id":x["id"],"type":x["type"],"stage":x.get("stage"),"unit":x["unit"],"path":x["path"]} for x in sorted(items, key=_nav_key)]}
    write_text(output / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    if open_browser:
        import webbrowser
        webbrowser.open((output / "index.html").as_uri())
    return output / "index.html"
