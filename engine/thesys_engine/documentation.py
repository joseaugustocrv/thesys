import hashlib
import html
import json
import re
from pathlib import Path
from .io import read_text, write_text
from .registry import get
from .workflow import _load_answers


LIFECYCLE = [
    ("intent", "INT", "Intent"),
    ("context", "CTX", "Context"),
    ("governance", "GOV", "Governance"),
    ("requirements", "REQUIREMENTS", "Requirements"),
    ("clarification", "CLARIFICATION", "Clarification"),
    ("specification", "SPECIFICATION", "Specification"),
    ("acceptance", "ACCEPTANCE", "Acceptance"),
    ("architecture", "ARCHITECTURE", "Architecture"),
    ("quality", "QUALITY", "Quality"),
    ("security", "SECURITY", "Security"),
    ("risk", "RISK", "Risk"),
    ("plan", "PLAN", "Plan"),
    ("tasks", "TASKS", "Tasks"),
    ("implementation", "IMPLEMENTATION", "Implementation"),
    ("verification", "VERIFICATION", "Verification"),
    ("convergence", "CONVERGENCE", "Convergence"),
    ("release", "RELEASE", "Release"),
    ("operation", "OPERATION", "Operation"),
    ("evolution", "EVOLUTION", "Evolution"),
    ("retirement", "RETIREMENT", "Retirement"),
]
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


def _markdown(text):
    lines = text.replace("\r\n", "\n").splitlines()
    out = []
    in_code = False
    code = []
    in_list = False
    for line in lines:
        if line.strip().startswith("```"):
            if in_code:
                out.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
                code = []
                in_code = False
            else:
                if in_list:
                    out.append("</ul>"); in_list = False
                in_code = True
            continue
        if in_code:
            code.append(line)
            continue
        if not line.strip():
            if in_list:
                out.append("</ul>"); in_list = False
            continue
        if line.startswith("#"):
            if in_list:
                out.append("</ul>"); in_list = False
            m = re.match(r"^(#{1,6})\s+(.*)$", line)
            if m:
                level = len(m.group(1)); title = _inline(m.group(2)); anchor = _slug(re.sub(r"<[^>]+>", "", title))
                out.append(f'<h{level} id="{anchor}">{title}</h{level}>')
                continue
        m = re.match(r"^\s*[-*]\s+(.*)$", line)
        if m:
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{_inline(m.group(1))}</li>")
            continue
        m = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if m:
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f'<p class="ordered-item">{_inline(m.group(1))}</p>')
            continue
        if line.startswith(">"):
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<blockquote>{_inline(line[1:].lstrip())}</blockquote>")
            continue
        if in_list:
            out.append("</ul>"); in_list = False
        out.append(f"<p>{_inline(line)}</p>")
    if in_list: out.append("</ul>")
    if in_code: out.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
    return "\n".join(out)


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
        items.append({
            "id": aid,
            "type": item.get("type", "artifact"),
            "unit": item.get("unit", "default"),
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


def _approval_state(project, item):
    approvals_path = project / ".thesys" / "approvals.json"
    try:
        approvals = json.loads(read_text(approvals_path)).get("approvals", {})
    except (OSError, json.JSONDecodeError):
        approvals = {}
    stage = next((key for key, code, _ in LIFECYCLE if code == item["type"]), item["type"].lower())
    approval = approvals.get(f"{stage}:{item['unit']}")
    if not approval:
        return {"state": "not-approved", "label": "Not approved", "approved_at": None}
    path = project / item["path"]
    try:
        current_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return {"state": "approval-unverified", "label": "Approval recorded; source unavailable", "approved_at": approval.get("approved_at")}
    if current_sha != approval.get("sha256"):
        return {"state": "approval-stale", "label": "Approval stale", "approved_at": approval.get("approved_at")}
    return {"state": "approved", "label": "Approved · authoritative", "approved_at": approval.get("approved_at")}


def _display_content(item, approval):
    if approval["state"] != "approved":
        return item["content"]
    text = item["content"]
    replacements = [
        (r"\*\*Status da proposta:\*\*[^\n]*", "**Status da proposta:** Autoritativa; aprovada humanamente."),
        (r"\*\*Status:\*\*\s*Draft;[^\n]*", "**Status:** Approved; authoritative artifact accepted by human approval."),
        (r"\*\*Status:\*\*\s*Draft[^\n]*", "**Status:** Approved; authoritative artifact accepted by human approval."),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, count=1, flags=re.IGNORECASE)
    return text


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
    stage = next((key for key, code, _ in LIFECYCLE if code == item["type"]), item["type"].lower())
    proposal = proposals.get(f"{stage}:{item['unit']}") or proposals.get(f"{stage}:default")
    questions = []
    if proposal:
        for q in proposal.get("questions", []):
            q = dict(q)
            q["answer"] = answers.get(q.get("id"), {}).get("answer")
            questions.append(q)
    return related, questions


def _site_html(project, items, proposals, answers):
    payload = []
    for item in items:
        related, questions = _related(project, item, items, proposals, answers)
        approval = _approval_state(project, item)
        payload.append({
            **{k: item[k] for k in ("id", "type", "unit", "status", "authority", "path", "title")},
            "html": _markdown(_display_content(item, approval)),
            "related": [x["id"] for x in related],
            "questions": questions,
            "approval": approval,
        })
    payload.sort(key=lambda x: _nav_key(x))
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    lifecycle = json.dumps(LIFECYCLE, ensure_ascii=False)
    project_name = project.name
    return _HTML.replace("__DATA__", data).replace("__LIFECYCLE__", lifecycle).replace("__PROJECT__", html.escape(project_name))


def _nav_key(item):
    t = item["type"].upper()
    if t in LIFECYCLE_TYPES:
        order = next(i for i, (_, code, _) in enumerate(LIFECYCLE) if code.upper() == t)
        return (0, order, item["unit"], item["id"])
    return (1, item["type"], item["unit"], item["id"])


_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Thesys — __PROJECT__ Documentation</title>
<link rel="stylesheet" href="styles.css">
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <div class="brand">THESYS <span>DOCUMENTATION</span></div>
    <div class="project-name">__PROJECT__</div>
    <div id="progress" class="progress"></div>
    <input id="search" type="search" placeholder="Search artifacts…" aria-label="Search artifacts">
    <div id="nav" class="nav"></div>
  </aside>
  <main class="content">
    <header class="topbar"><div id="crumb">Project documentation</div><button id="copy-link">Copy link</button></header>
    <article id="document" class="document"></article>
  </main>
  <aside class="related">
    <h2>References</h2>
    <section id="approval-panel"></section>
    <section><h3>Related artifacts</h3><div id="related-artifacts"></div></section>
    <section><h3>Questions & answers</h3><div id="questions"></div></section>
    <section><h3>Metadata</h3><dl id="metadata"></dl></section>
  </aside>
</div>
<script>
const DATA = __DATA__;
const LIFECYCLE = __LIFECYCLE__;
const byId = Object.fromEntries(DATA.map(x => [x.id, x]));
const nav = document.getElementById('nav');
const doc = document.getElementById('document');
const related = document.getElementById('related-artifacts');
const questions = document.getElementById('questions');
const metadata = document.getElementById('metadata');
const approvalPanel = document.getElementById('approval-panel');
const progress = document.getElementById('progress');
const search = document.getElementById('search');
let current = null;
function esc(s){ const d=document.createElement('div'); d.textContent=s ?? ''; return d.innerHTML; }
function stageItems(keyOrCode){ const stage=LIFECYCLE.find(([key,code]) => key.toLowerCase()===keyOrCode.toLowerCase() || code.toLowerCase()===keyOrCode.toLowerCase()); if(!stage) return []; const [key,code]=stage; return DATA.filter(x => x.type.toLowerCase()===key.toLowerCase() || x.type.toLowerCase()===code.toLowerCase()); }
function renderNav(filter=''){
  const q=filter.toLowerCase();
  const lifecycleHtml = LIFECYCLE.map(([key,code,label]) => {
    const xs=stageItems(key).filter(x => !q || `${x.id} ${x.title} ${x.path}`.toLowerCase().includes(q));
    const existing=stageItems(key);
    if(q && !xs.length) return '';
    if(!existing.length) return `<div class="nav-stage missing"><span class="stage-dot"></span><div><strong>${esc(label)}</strong><small>Not generated</small></div></div>`;
    return xs.sort((a,b)=>a.id.localeCompare(b.id)).map(x=>`<button class="nav-item" data-id="${esc(x.id)}"><span>${esc(label)} · ${esc(x.id)}</span><small>${esc(x.title)}</small></button>`).join('');
  }).join('');
  const supportTypes=[...new Set(DATA.map(x=>x.type).filter(t=>!LIFECYCLE.some(([,code])=>code.toUpperCase()===t.toUpperCase())))].sort();
  const supportHtml=supportTypes.map(type=>{
    const xs=DATA.filter(x=>x.type===type && (!q || `${x.id} ${x.title} ${x.path}`.toLowerCase().includes(q)));
    if(!xs.length) return '';
    return `<div class="nav-group"><div class="nav-title">${esc(type)}</div>${xs.sort((a,b)=>a.id.localeCompare(b.id)).map(x=>`<button class="nav-item" data-id="${esc(x.id)}"><span>${esc(x.id)}</span><small>${esc(x.title)}</small></button>`).join('')}</div>`;
  }).join('');
  nav.innerHTML=`<div class="nav-section"><div class="nav-title">Lifecycle</div>${lifecycleHtml}</div>${supportHtml?`<div class="nav-section support"><div class="nav-title">Supporting artifacts</div>${supportHtml}</div>`:''}`;
  nav.querySelectorAll('[data-id]').forEach(b => b.onclick=()=>select(b.dataset.id));
}
function renderProgress(){
  const total=LIFECYCLE.length;
  const generated=LIFECYCLE.filter(([key,code])=>stageItems(code).length).length;
  const approved=LIFECYCLE.filter(([key,code])=>stageItems(code).some(x=>x.approval?.state==='approved')).length;
  progress.innerHTML=`<div class="progress-label"><strong>${generated}/${total}</strong> lifecycle stages documented</div><div class="progress-bar"><span style="width:${(generated/total)*100}%"></span></div><small>${approved} approved · ${total-generated} not generated</small>`;
}
function select(id, push=true){
  const x=byId[id]; if(!x) return;
  current=x;
  doc.innerHTML=x.html;
  document.getElementById('crumb').textContent=`${x.id} · ${x.title}`;
  approvalPanel.innerHTML=`<div class="approval ${esc(x.approval?.state||'not-approved')}"><strong>${esc(x.approval?.label||'Approval state unavailable')}</strong>${x.approval?.approved_at?`<small>Approved ${esc(new Date(x.approval.approved_at).toLocaleString())}</small>`:''}</div>`;
  related.innerHTML=(x.related||[]).map(id=>{const r=byId[id]; return r?`<button class="ref" data-id="${esc(id)}"><strong>${esc(id)}</strong><span>${esc(r.title)}</span></button>`:''}).join('') || '<p class="muted">No related artifacts found.</p>';
  related.querySelectorAll('[data-id]').forEach(b=>b.onclick=()=>select(b.dataset.id));
  questions.innerHTML=(x.questions||[]).map(q=>`<div class="question"><strong>${esc(q.id)}</strong><p>${esc(q.question)}</p><span class="badge ${q.blocking?'blocking':'nonblocking'}">${q.blocking?'blocking':'non-blocking'}</span>${q.answer?`<div class="answer"><b>Answer</b><p>${esc(q.answer)}</p></div>`:'<div class="muted">Unanswered</div>'}</div>`).join('') || '<p class="muted">No proposal questions for this artifact.</p>';
  metadata.innerHTML=`<dt>Project state</dt><dd>${esc(x.approval?.label||'Unknown')}</dd><dt>Registry status</dt><dd>${esc(x.status)}</dd><dt>Authority</dt><dd>${esc(x.authority)}</dd><dt>Unit</dt><dd>${esc(x.unit)}</dd><dt>Path</dt><dd><code>${esc(x.path)}</code></dd>`;
  document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.id===id));
  if(push) history.replaceState(null,'',`#${encodeURIComponent(id)}`);
}
search.oninput=()=>renderNav(search.value);
document.getElementById('copy-link').onclick=()=>navigator.clipboard?.writeText(location.href);
renderProgress();
renderNav();
const initial=decodeURIComponent(location.hash.slice(1));
const first=LIFECYCLE.flatMap(([key,code])=>stageItems(code)).find(Boolean)?.id || DATA[0]?.id;
select(byId[initial]?initial:first,false);
</script>
</body>
</html>'''

_CSS = r''':root{color-scheme:light;--border:#e2e5e9;--muted:#68717c;--bg:#f6f7f9;--panel:#fff;--accent:#24292f;--ok:#176b3a;--okbg:#e8f5ed}*{box-sizing:border-box}body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;color:#20252b;background:var(--bg)}button,input{font:inherit}.app{display:grid;grid-template-columns:292px minmax(0,1fr) 340px;height:100vh}.sidebar,.related{background:var(--panel);overflow:auto}.sidebar{border-right:1px solid var(--border);padding:18px}.related{border-left:1px solid var(--border);padding:22px}.brand{font-weight:800;letter-spacing:.08em;margin-bottom:3px}.brand span{font-size:10px;color:var(--muted);font-weight:600;display:block;letter-spacing:.16em;margin-top:3px}.project-name{font-size:13px;font-weight:650;margin:14px 0 12px}.progress{padding:10px 0 14px;border-bottom:1px solid var(--border);margin-bottom:14px}.progress-label{font-size:12px;color:#343a40}.progress-label strong{font-size:14px}.progress small{display:block;color:var(--muted);margin-top:5px}.progress-bar{height:5px;background:#edf0f2;border-radius:5px;overflow:hidden;margin-top:7px}.progress-bar span{display:block;height:100%;background:#20252b;border-radius:5px}#search{width:100%;padding:9px 10px;border:1px solid var(--border);border-radius:7px;margin-bottom:16px}.nav-section{margin:0 0 20px}.nav-title{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:700;margin:0 0 5px}.nav-stage{display:flex;gap:8px;align-items:center;padding:7px 8px;color:#4b535b}.nav-stage strong{display:block;font-size:12px}.nav-stage small{display:block;color:var(--muted);font-size:11px;margin-top:2px}.stage-dot{width:7px;height:7px;border-radius:50%;background:#b9c0c7;flex:0 0 auto}.nav-item,.ref{width:100%;text-align:left;background:none;border:0;border-radius:6px;padding:8px;cursor:pointer}.nav-item:hover,.nav-item.active,.ref:hover{background:#f0f2f4}.nav-item span{display:block;font-size:12px;font-weight:700}.nav-item small,.ref span{display:block;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px}.support{padding-top:4px;border-top:1px solid var(--border)}.content{overflow:auto;background:#fff}.topbar{position:sticky;top:0;background:rgba(255,255,255,.94);backdrop-filter:blur(8px);border-bottom:1px solid var(--border);height:58px;padding:0 32px;display:flex;align-items:center;justify-content:space-between;color:var(--muted);font-size:13px}.topbar button{border:1px solid var(--border);background:#fff;border-radius:6px;padding:6px 10px;cursor:pointer}.document{max-width:900px;margin:0 auto;padding:42px 52px 80px}.document h1,.document h2,.document h3{scroll-margin-top:80px}.document h1{font-size:32px}.document h2{margin-top:34px;border-bottom:1px solid var(--border);padding-bottom:8px}.document p,.document li{line-height:1.65}.document pre{background:#f3f4f6;padding:14px;border-radius:8px;overflow:auto}.document code{background:#f1f2f3;padding:2px 4px;border-radius:4px}.document pre code{background:none;padding:0}.document blockquote{border-left:3px solid #ccd1d6;padding-left:14px;color:var(--muted)}.related h2{margin:0 0 18px}.related h3{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}.related section{margin-bottom:24px}.approval{padding:11px 12px;border-radius:8px;background:#f3f4f6;border:1px solid var(--border)}.approval.approved{background:var(--okbg);border-color:#c9e5d5;color:var(--ok)}.approval small{display:block;margin-top:4px;color:var(--muted);font-size:11px}.ref{border-bottom:1px solid var(--border);padding:9px 2px}.ref strong{display:block}.question{border-bottom:1px solid var(--border);padding:10px 0}.question p{font-size:13px;line-height:1.45}.badge{font-size:10px;text-transform:uppercase;letter-spacing:.06em;padding:3px 6px;border-radius:10px;background:#eef0f2}.blocking{background:#f5dddd}.nonblocking{background:#e6f1e7}.answer{margin-top:10px;padding:9px;background:#f7f8f9;border-radius:6px}.answer p{margin-bottom:0}.muted{color:var(--muted);font-size:13px}.related dl{display:grid;grid-template-columns:92px 1fr;gap:7px;font-size:12px}.related dt{color:var(--muted)}.related dd{margin:0;overflow-wrap:anywhere}@media(max-width:1100px){.app{grid-template-columns:230px minmax(0,1fr)}.related{display:none}}@media(max-width:700px){.app{display:block}.sidebar{height:auto;max-height:40vh;border-right:0;border-bottom:1px solid var(--border)}.content{height:60vh}.document{padding:28px 20px 50px}.topbar{padding:0 18px}}
'''


def build_documentation(project, output=None, open_browser=False):
    project = Path(project).resolve()
    if not (project / ".thesys").is_dir():
        raise ValueError(f"Not a Thesys project: {project}")
    output = Path(output).resolve() if output else project / ".thesys" / "docs"
    output.mkdir(parents=True, exist_ok=True)
    items = _artifact_items(project)
    proposals = _proposals(project)
    answers = _load_answers(project)
    write_text(output / "index.html", _site_html(project, items, proposals, answers))
    write_text(output / "styles.css", _CSS)
    manifest = {"schema":"1","generated_by":"thesys docs build","artifact_count":len(items),"artifacts":[{"id":x["id"],"type":x["type"],"unit":x["unit"],"path":x["path"]} for x in sorted(items, key=_nav_key)]}
    write_text(output / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    if open_browser:
        import webbrowser
        webbrowser.open((output / "index.html").as_uri())
    return output / "index.html"
