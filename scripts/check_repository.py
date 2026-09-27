from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]

for path in ROOT.rglob("*"):
    if ".git" in path.parts:
        continue
    if "baseline" in {part.lower() for part in path.parts}:
        print(f"Unexpected baseline content: {path.relative_to(ROOT)}")
        sys.exit(1)

for path in ROOT.rglob("*.md"):
    if ".git" in path.parts:
        continue
    text = path.read_text(encoding="utf-8")
    if "\ufeff" in text:
        print(f"BOM found in {path.relative_to(ROOT)}")
        sys.exit(1)

print("Repository consistency checks passed.")
