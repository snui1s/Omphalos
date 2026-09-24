# indexer/cache.py
import hashlib
import json
import os
import tempfile
from pathlib import Path

CACHE_FILE = ".llm_cache.json"
# เพิ่มเลขนี้เมื่อโครงสร้างข้อมูลใน cache เปลี่ยน เพื่อบังคับ parse ใหม่ทั้งหมด
CACHE_VERSION = 2

def calculate_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def load_cache(root_dir: Path) -> dict:
    cache_path = root_dir / CACHE_FILE
    if not cache_path.exists():
        return {}
    try:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return {}
    # ทิ้ง cache ที่สร้างจากโครงสร้างข้อมูลคนละเวอร์ชัน
    if not isinstance(raw, dict) or raw.get("version") != CACHE_VERSION:
        return {}
    files = raw.get("files")
    return files if isinstance(files, dict) else {}

def save_cache(root_dir: Path, cache: dict):
    """เขียน cache แบบ atomic (temp file + os.replace) กันไฟล์เสียหายเมื่อถูกขัดกลางคัน"""
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
