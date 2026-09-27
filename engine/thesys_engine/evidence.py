import json
from datetime import datetime, timezone
from .io import write_text
from .registry import allocate_id, add_relation, register_artifact


def record(project, subject, result, evidence_type="verification", source="cli", scope="", tool="thesys", tool_version="", related=None):
    eid=allocate_id(project,"EVD")
    payload={
      "id":eid,"type":evidence_type,"source":source,"timestamp":datetime.now(timezone.utc).isoformat(),
      "subject":subject,"scope":scope,"tool":tool,"tool_version":tool_version,"result":result,
      "related_artifacts":related or []
    }
    p=project/".thesys"/"evidence"/f"{eid}.json"; p.parent.mkdir(parents=True,exist_ok=True)
    write_text(p,json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
    register_artifact(project,eid,"EVD",p,"system",status="authoritative",authority="system")
    for aid in related or []: add_relation(project,aid,"evidences",eid)
    return p
