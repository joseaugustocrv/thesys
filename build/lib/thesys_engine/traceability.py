from .registry import get


def graph(project, root):
    data=get(project); edges=data.get("relations",[]); seen={root}; queue=[root]; out=[]
    while queue:
        cur=queue.pop(0)
        for e in edges:
            if e["source"]==cur and e["target"] not in seen:
                seen.add(e["target"]); queue.append(e["target"]); out.append(e)
    return out


def reverse_graph(project, target):
    data=get(project); return [e for e in data.get("relations",[]) if e["target"]==target]
