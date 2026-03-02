from pathlib import Path
import re

ALLOWED_EXTS = {".java", ".c", ".cpp"}

def _strip_comments(text: str) -> str:
    # basic remover; keep off if your prof disallows stripping
    text = re.sub(r"//.*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return text

def canonicalize(sub_dir: Path, strip_comments: bool = False) -> Path:
    roots = [sub_dir]
    extracted = sub_dir / "extracted"
    if extracted.exists():
        roots.append(extracted)

    files = []
    for r in roots:
        for p in r.rglob("*"):
            if p.is_file() and p.suffix.lower() in ALLOWED_EXTS:
                files.append(p)

    # deterministic order
    files.sort(key=lambda p: str(p.relative_to(sub_dir)))

    out = sub_dir / "canonical.txt"
    parts = []
    for f in files:
        rel = f.relative_to(sub_dir)
        parts.append(f"\n<<<FILE:{rel.as_posix()}>>>\n")
        t = f.read_text(encoding="utf-8", errors="ignore")
        if strip_comments:
            t = _strip_comments(t)
        parts.append(t)

    out.write_text("".join(parts), encoding="utf-8")
    return out