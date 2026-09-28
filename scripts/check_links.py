from pathlib import Path
import re, sys
ROOT=Path(__file__).parents[1]
pattern=re.compile(r"\[[^\]]+\]\(([^)]+)\)")
errors=[]
for md in ROOT.rglob("*.md"):
    if any(part in {'.git', '.venv', 'build', 'dist'} for part in md.parts): continue
    text=md.read_text(encoding="utf-8")
    for target in pattern.findall(text):
        if target.startswith(("http://","https://","#","mailto:")): continue
        target=target.split("#",1)[0]
        p=(md.parent/target).resolve()
        if not p.exists(): errors.append(f"{md.relative_to(ROOT)} -> {target}")
if errors:
    print("Broken documentation links:")
    print("\n".join(errors)); sys.exit(1)
print("Documentation links passed.")
