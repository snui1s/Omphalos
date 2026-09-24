# tests/test_cache.py
import json
from pathlib import Path

import pytest

from omphalos.cache import CACHE_FILE, CACHE_VERSION, calculate_sha256, load_cache, save_cache


def test_sha256_known_value():
    assert calculate_sha256(b"hello") == (
        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


def test_load_cache_missing_file(tmp_path: Path):
    assert load_cache(tmp_path) == {}


def test_load_cache_corrupt_json(tmp_path: Path):
    (tmp_path / CACHE_FILE).write_text("{not json", encoding="utf-8")
    assert load_cache(tmp_path) == {}


def test_load_cache_old_version_is_discarded(tmp_path: Path):
    (tmp_path / CACHE_FILE).write_text(
        json.dumps({"version": CACHE_VERSION - 1, "files": {"a.py": {"hash": "x"}}}),
        encoding="utf-8",
    )
    assert load_cache(tmp_path) == {}


def test_load_cache_legacy_format_is_discarded(tmp_path: Path):
    # cache รูปแบบเก่า (ก่อนมี version) ต้องถูกทิ้ง ไม่ใช่โหลดมาใช้
    (tmp_path / CACHE_FILE).write_text(
        json.dumps({"a.py": {"hash": "x", "data": {"symbols": []}}}),
        encoding="utf-8",
    )
    assert load_cache(tmp_path) == {}


def test_save_and_load_roundtrip(tmp_path: Path):
    files = {"a.py": {"hash": "deadbeef", "data": {"symbols": [{"kind": "function", "name": "a"}]}}}
    save_cache(tmp_path, files)
    assert load_cache(tmp_path) == files

    raw = json.loads((tmp_path / CACHE_FILE).read_text(encoding="utf-8"))
    assert raw["version"] == CACHE_VERSION


def test_save_cache_is_atomic_on_failure(tmp_path: Path):
    cache_path = tmp_path / CACHE_FILE
    save_cache(tmp_path, {"a.py": {"hash": "h", "data": {"symbols": []}}})
    before = cache_path.read_text(encoding="utf-8")

    # object() serialize ไม่ได้ → json.dump ต้อง raise กลางทาง
    with pytest.raises(TypeError):
        save_cache(tmp_path, {"a.py": {"hash": "h", "data": object()}})

    # ไฟล์เดิมต้องไม่เสีย และไม่เหลือ temp file ค้าง
    assert cache_path.read_text(encoding="utf-8") == before
    assert list(tmp_path.glob("*.tmp")) == []
