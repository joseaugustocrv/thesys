from .registry import allocate_id, add_event, get, register_artifact, add_relation
from .io import write_text
import json
from datetime import datetime, timezone


def create_change(project, title, description, unit):
    cid=allocate_id(project,"CHG")
    p=project/".thesys"/"changes"/f"{cid}.json"; p.parent.mkdir(parents=True,exist_ok=True)
    payload={"id":cid,"title":title,"description":description,"unit":unit,"status":"proposed","created_at":datetime.now(timezone.utc).isoformat()}
    write_text(p,json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
    register_artifact(project,cid,"CHG",p,unit,status="proposed",authority="human")
    add_event(project,"change-created",cid,{"unit":unit})
    return p


def impact(project, change_id):
    data=get(project); direct=[]
    for e in data.get("relations",[]):
        if e["source"]==change_id or e["target"]==change_id: direct.append(e)
    return direct
