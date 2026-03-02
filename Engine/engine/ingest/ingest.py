import shutil, zipfile
from pathlib import Path

ALLOWED_EXTS = {".java", ".c",".cpp"}

class UnsafeZipError(Exception):
    pass

def _safe_extract(zip_path: Path, dest: Path, max_files: int = 500):
    with zipfile.ZipFile(zip_path, "r") as z:
        infos = z.infolist()
        if len(infos) > max_files:
            raise UnsafeZipError("Zip has too many files")

        dest_resolved = dest.resolve()
        for info in infos:
            out = (dest / info.filename).resolve()
            if not str(out).startswith(str(dest_resolved)):
                raise UnsafeZipError("Zip contains unsafe path traversal")

        z.extractall(dest)

def ingest_to_dir(upload: Path, out_dir: Path) -> Path:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    upload = upload.resolve()
    if upload.suffix.lower() == ".zip":
        _safe_extract(upload, out_dir / "extracted")
        return out_dir
    else:
        if upload.suffix.lower() not in ALLOWED_EXTS:
            raise ValueError(f"Unsupported file type: {upload.suffix}")
        shutil.copy2(upload, out_dir / upload.name)
        return out_dir