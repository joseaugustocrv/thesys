from pathlib import Path

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")

def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Emit standards-compliant UTF-8 without a BOM. ``read_text`` accepts both
    # BOM and BOM-less legacy artifacts so existing projects remain readable.
    path.write_text(content.replace("\ufeff", ""), encoding="utf-8")
