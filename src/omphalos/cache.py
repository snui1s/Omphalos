# omphalos/cache.py
import hashlib
import json
import os
import tempfile
from pathlib import Path

CACHE_FILE = ".omphalos_cache.json"
# Increment this number when the cache data structure changes to invalidate old caches.
# v3: symbols stored as structured dicts (kind/name/line/doc/label/children)
CACHE_VERSION = 3

def calculate_sha256(content: bytes) -> str:
    """Calculate the SHA-256 checksum of raw file bytes for change detection."""
    return hashlib.sha256(content).hexdigest()

def load_cache(root_dir: Path) -> dict:
    """Load symbol cache from .omphalos_cache.json.
    
    Returns an empty dict if the cache file does not exist, fails to parse,
    or has an incompatible cache version.
    """
    cache_path = root_dir / CACHE_FILE
    if not cache_path.exists():
        return {}
    try:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return {}
    # Discard cache created with a different schema version
    if not isinstance(raw, dict) or raw.get("version") != CACHE_VERSION:
        return {}
    files = raw.get("files")
    return files if isinstance(files, dict) else {}

def save_cache(root_dir: Path, cache: dict):
    """Save symbol cache to .omphalos_cache.json atomically.
    
    Writes to a temporary file first and replaces the target file via os.replace
    to prevent file corruption if interrupted.
    """
    cache_path = root_dir / CACHE_FILE
    payload = {"version": CACHE_VERSION, "files": cache}
    fd, tmp_name = tempfile.mkstemp(
        dir=cache_path.parent, prefix=f"{CACHE_FILE}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        os.replace(tmp_name, cache_path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
