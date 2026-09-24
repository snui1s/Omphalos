# tests/test_cli.py
import json
from pathlib import Path

import typer
from typer.testing import CliRunner

from llm_indexer.cli import app

runner = CliRunner()

SAMPLE_PY = """\
class Foo:
    \"\"\"Handles foo things.\"\"\"

    def bar(self):
        pass


def top_level():
    pass
"""


def test_scan_generates_index_and_cache(tmp_path: Path):
    (tmp_path / "mymod.py").write_text(SAMPLE_PY, encoding="utf-8")
    (tmp_path / "notes.txt").write_text("not code", encoding="utf-8")

    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0, result.output

    index = (tmp_path / ".llm_index").read_text(encoding="utf-8")
    assert "## mymod.py" in index
    assert "- class `Foo`: Handles foo things." in index
    assert "- `top_level()`" in index
    assert "notes.txt" not in index

    raw = json.loads((tmp_path / ".llm_cache.json").read_text(encoding="utf-8"))
    assert raw["version"] == 2
    assert "mymod.py" in raw["files"]


def test_scan_reuses_cache_without_reparsing(tmp_path: Path, monkeypatch):
    (tmp_path / "mymod.py").write_text(SAMPLE_PY, encoding="utf-8")
    assert runner.invoke(app, ["scan", str(tmp_path)]).exit_code == 0

    # ดองข้อมูลใน cache แล้วสั่งห้าม parse — ถ้า cache ถูกใช้ ผลลัพธ์ต้องติด POISONED
    cache_path = tmp_path / ".llm_cache.json"
    raw = json.loads(cache_path.read_text(encoding="utf-8"))
    raw["files"]["mymod.py"]["data"] = {"symbols": ["- POISONED"]}
    cache_path.write_text(json.dumps(raw), encoding="utf-8")

    def explode(*args, **kwargs):
        raise AssertionError("extract_symbols must not be called on cache hit")

    monkeypatch.setattr("llm_indexer.cli.extract_symbols", explode)

    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0, result.output
    index = (tmp_path / ".llm_index").read_text(encoding="utf-8")
    assert "- POISONED" in index


def test_scan_corrupt_cache_entry_falls_back_to_reparse(tmp_path: Path):
    (tmp_path / "mymod.py").write_text(SAMPLE_PY, encoding="utf-8")
    assert runner.invoke(app, ["scan", str(tmp_path)]).exit_code == 0

    cache_path = tmp_path / ".llm_cache.json"
    raw = json.loads(cache_path.read_text(encoding="utf-8"))
    del raw["files"]["mymod.py"]["data"]  # entry ที่พังต้อง re-parse ไม่ crash
    cache_path.write_text(json.dumps(raw), encoding="utf-8")

    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0, result.output
    index = (tmp_path / ".llm_index").read_text(encoding="utf-8")
    assert "- class `Foo`" in index


def test_scan_reports_parse_errors(tmp_path: Path, monkeypatch):
    (tmp_path / "broken.py").write_text("x = 1\n", encoding="utf-8")

    monkeypatch.setattr(
        "llm_indexer.cli.extract_symbols",
        lambda *a, **k: {"error": "boom", "symbols": []},
    )
    echoed = []
    monkeypatch.setattr(typer, "echo", lambda msg="", **k: echoed.append(str(msg)))

    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    # error ต่อไฟล์ต้องถูกรายงาน ไม่กลืนหาย
    assert any("broken.py" in msg and "boom" in msg for msg in echoed)
    assert any("1 failed" in msg for msg in echoed)

    # index ยังต้องถูกเขียน แต่ไม่มีสัญลักษณ์ของไฟล์ที่พัง
    assert (tmp_path / ".llm_index").exists()


def test_scan_no_failure_summary_when_all_ok(tmp_path: Path, monkeypatch):
    (tmp_path / "ok.py").write_text("def f():\n    pass\n", encoding="utf-8")

    echoed = []
    monkeypatch.setattr(typer, "echo", lambda msg="", **k: echoed.append(str(msg)))

    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert any("successfully" in msg for msg in echoed)
    assert not any("failed" in msg for msg in echoed)
