from pathlib import Path

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")

def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoding = "utf-8-sig" if path.suffix.lower() in {".md", ".txt"} else "utf-8"
    path.write_text(content.replace("\ufeff", ""), encoding=encoding)
