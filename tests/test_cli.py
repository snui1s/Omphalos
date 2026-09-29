# tests/test_cli.py
import json
import shutil
import subprocess
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from omphalos.cache import CACHE_FILE, CACHE_VERSION
from omphalos.cli import INDEX_FILE, app

runner = CliRunner()

SAMPLE_PY = """\
class Foo:
    \"\"\"Handles foo things.\"\"\"

    def bar(self):
        pass


def top_level():
    pass
"""

# สัญลักษณ์ปลอมสำหรับดอง cache — ถ้าผลลัพธ์ scan ติดคำนี้แปลว่า cache ถูกใช้จริง
POISONED_SYMBOL = {
    "label": "POISONED", "name": "p", "kind": "function",
    "line": 1, "doc": "", "exported": False, "children": [],
}


def scan(tmp_path: Path, *args):
    return runner.invoke(app, ["scan", str(tmp_path), *args])


def test_scan_generates_index_and_cache(tmp_path: Path):
    (tmp_path / "mymod.py").write_text(SAMPLE_PY, encoding="utf-8")
    (tmp_path / "notes.txt").write_text("not code", encoding="utf-8")

    result = scan(tmp_path)
    assert result.exit_code == 0, result.output

    index = (tmp_path / INDEX_FILE).read_text(encoding="utf-8")
    assert "## mymod.py" in index
    assert "- class `Foo` @1: Handles foo things." in index
    assert "  - `bar()` @4" in index
    assert "- `top_level()` @8" in index
    assert "notes.txt" not in index

    raw = json.loads((tmp_path / CACHE_FILE).read_text(encoding="utf-8"))
    assert raw["version"] == CACHE_VERSION
    assert "mymod.py" in raw["files"]


def test_scan_reuses_cache_without_reparsing(tmp_path: Path, monkeypatch):
    (tmp_path / "mymod.py").write_text(SAMPLE_PY, encoding="utf-8")
    assert scan(tmp_path).exit_code == 0

    # ดองข้อมูลใน cache แล้วสั่งห้าม parse — ถ้า cache ถูกใช้ ผลลัพธ์ต้องติด POISONED
    cache_path = tmp_path / CACHE_FILE
    raw = json.loads(cache_path.read_text(encoding="utf-8"))
    raw["files"]["mymod.py"]["data"] = {"symbols": [POISONED_SYMBOL]}
    cache_path.write_text(json.dumps(raw), encoding="utf-8")

    def explode(*args, **kwargs):
        raise AssertionError("extract_symbols must not be called on cache hit")

    monkeypatch.setattr("omphalos.cli.extract_symbols", explode)

    result = scan(tmp_path)
    assert result.exit_code == 0, result.output
    index = (tmp_path / INDEX_FILE).read_text(encoding="utf-8")
    assert "- POISONED @1" in index


def test_scan_no_cache_ignores_poisoned_cache(tmp_path: Path):
    (tmp_path / "mymod.py").write_text(SAMPLE_PY, encoding="utf-8")
    assert scan(tmp_path).exit_code == 0

    cache_path = tmp_path / CACHE_FILE
    raw = json.loads(cache_path.read_text(encoding="utf-8"))
    raw["files"]["mymod.py"]["data"] = {"symbols": [POISONED_SYMBOL]}
    cache_path.write_text(json.dumps(raw), encoding="utf-8")

    result = scan(tmp_path, "--no-cache")
    assert result.exit_code == 0, result.output
    index = (tmp_path / INDEX_FILE).read_text(encoding="utf-8")
    assert "POISONED" not in index
    assert "- class `Foo` @1" in index


def test_scan_corrupt_cache_entry_falls_back_to_reparse(tmp_path: Path):
    (tmp_path / "mymod.py").write_text(SAMPLE_PY, encoding="utf-8")
    assert scan(tmp_path).exit_code == 0

    cache_path = tmp_path / CACHE_FILE
    raw = json.loads(cache_path.read_text(encoding="utf-8"))
    del raw["files"]["mymod.py"]["data"]  # entry ที่พังต้อง re-parse ไม่ crash
    cache_path.write_text(json.dumps(raw), encoding="utf-8")

    result = scan(tmp_path)
    assert result.exit_code == 0, result.output
    index = (tmp_path / INDEX_FILE).read_text(encoding="utf-8")
    assert "- class `Foo`" in index


def test_scan_reports_parse_errors(tmp_path: Path, monkeypatch):
    (tmp_path / "broken.py").write_text("x = 1\n", encoding="utf-8")

    monkeypatch.setattr(
        "omphalos.cli.extract_symbols",
        lambda *a, **k: {"error": "boom", "symbols": []},
    )
    echoed = []
    monkeypatch.setattr(typer, "echo", lambda msg="", **k: echoed.append(str(msg)))

    result = scan(tmp_path)
    assert result.exit_code == 0
    # error ต่อไฟล์ต้องถูกรายงาน ไม่กลืนหาย
    assert any("broken.py" in msg and "boom" in msg for msg in echoed)
    assert any("1 failed" in msg for msg in echoed)

    # index ยังต้องถูกเขียน แต่ไม่มีสัญลักษณ์ของไฟล์ที่พัง
    assert (tmp_path / INDEX_FILE).exists()


def test_scan_no_failure_summary_when_all_ok(tmp_path: Path, monkeypatch):
    (tmp_path / "ok.py").write_text("def f():\n    pass\n", encoding="utf-8")

    echoed = []
    monkeypatch.setattr(typer, "echo", lambda msg="", **k: echoed.append(str(msg)))

    result = scan(tmp_path)
    assert result.exit_code == 0
    assert any("successfully" in msg for msg in echoed)
    assert not any("failed" in msg for msg in echoed)


def test_scan_json_format(tmp_path: Path):
    (tmp_path / "mymod.py").write_text(SAMPLE_PY, encoding="utf-8")
    result = scan(tmp_path, "--format", "json")
    assert result.exit_code == 0, result.output

    payload = json.loads((tmp_path / INDEX_FILE).read_text(encoding="utf-8"))
    assert payload["tool"] == "omphalos"
    assert payload["format_version"] == 1
    syms = payload["files"]["mymod.py"]["symbols"]
    cls = next(s for s in syms if s["name"] == "Foo")
    assert cls["kind"] == "class"
    assert cls["line"] == 1
    assert cls["doc"] == "Handles foo things."
    assert cls["children"][0]["name"] == "bar"
    assert cls["children"][0]["line"] == 4


def test_scan_rejects_invalid_format(tmp_path: Path):
    result = scan(tmp_path, "--format", "xml")
    assert result.exit_code == 2


def test_scan_output_to_custom_path(tmp_path: Path):
    (tmp_path / "ok.py").write_text("def f():\n    pass\n", encoding="utf-8")
    out = tmp_path / "custom" / "idx.md"
    out.parent.mkdir()
    result = scan(tmp_path, "--output", str(out))
    assert result.exit_code == 0, result.output
    assert "`f()`" in out.read_text(encoding="utf-8")
    assert not (tmp_path / INDEX_FILE).exists()


def test_check_passes_when_fresh(tmp_path: Path):
    (tmp_path / "mymod.py").write_text(SAMPLE_PY, encoding="utf-8")
    assert scan(tmp_path).exit_code == 0
    result = scan(tmp_path, "--check")
    assert result.exit_code == 0, result.output
    assert "up to date" in result.output


def test_check_fails_when_stale_and_writes_nothing(tmp_path: Path):
    (tmp_path / "mymod.py").write_text(SAMPLE_PY, encoding="utf-8")
    assert scan(tmp_path).exit_code == 0

    (tmp_path / "mymod.py").write_text(SAMPLE_PY + "\ndef extra():\n    pass\n", encoding="utf-8")
    result = scan(tmp_path, "--check")
    assert result.exit_code == 1

    # --check ต้องไม่เขียนไฟล์ใด ๆ
    index = (tmp_path / INDEX_FILE).read_text(encoding="utf-8")
    assert "extra" not in index


def test_check_fails_when_index_missing(tmp_path: Path):
    (tmp_path / "ok.py").write_text("def f():\n    pass\n", encoding="utf-8")
    result = scan(tmp_path, "--check")
    assert result.exit_code == 1


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "omphalos" in result.output


def test_no_args_shows_help():
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Commands" in result.output
    assert "scan" in result.output
    assert "init" in result.output


GIT_AVAILABLE = shutil.which("git") is not None


@pytest.mark.skipif(not GIT_AVAILABLE, reason="git not available")
def test_git_only_scans_only_tracked_files(tmp_path: Path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "tracked.py").write_text("def t():\n    pass\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.py"], cwd=tmp_path, check=True)
    (tmp_path / "untracked.py").write_text("def u():\n    pass\n", encoding="utf-8")

    result = scan(tmp_path, "--git-only")
    assert result.exit_code == 0, result.output
    index = (tmp_path / INDEX_FILE).read_text(encoding="utf-8")
    assert "tracked.py" in index
    assert "untracked.py" not in index


@pytest.mark.skipif(not GIT_AVAILABLE, reason="git not available")
def test_git_only_outside_repo_fails(tmp_path: Path):
    result = scan(tmp_path, "--git-only")
    assert result.exit_code == 1
    assert "git" in result.output.lower()
