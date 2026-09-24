# tests/test_parser.py
from pathlib import Path

from llm_indexer.parser import extract_symbols


def test_extract_python_with_content_bytes():
    p = Path("unused.py")
    content = (
        'class A:\n    """Doc."""\n    def m(self):\n        pass\n\n'
        "def f():\n    pass\n"
    ).encode("utf-8")
    assert extract_symbols(p, content)["symbols"] == [
        "- class `A`: Doc.",
        "  - `m()`",
        "- `f()`",
    ]


def test_extract_symbols_reads_file_when_no_content(tmp_path: Path):
    p = tmp_path / "m.py"
    p.write_text("def f():\n    pass\n", encoding="utf-8")
    assert extract_symbols(p)["symbols"] == ["- `f()`"]


def test_extract_symbols_empty_content(tmp_path: Path):
    assert extract_symbols(tmp_path / "e.py", b"") == {"symbols": []}


def test_extract_symbols_unknown_extension(tmp_path: Path):
    assert extract_symbols(tmp_path / "x.txt", b"anything") == {"symbols": []}


def test_extract_fixture_ts():
    fixture = Path(__file__).parent / "fixtures" / "sample.ts"
    joined = "\n".join(extract_symbols(fixture)["symbols"])
    assert "export interface `UserProfile`" in joined
    assert "export function `verifyToken()`" in joined
    assert "- export class `SessionManager`" in joined


def test_extract_fixture_go():
    fixture = Path(__file__).parent / "fixtures" / "sample.go"
    joined = "\n".join(extract_symbols(fixture)["symbols"])
    assert "- type `Account` (struct)" in joined
    assert "- func `(a *Account) Deposit()`" in joined


def test_extract_fixture_rust():
    fixture = Path(__file__).parent / "fixtures" / "sample.rs"
    joined = "\n".join(extract_symbols(fixture)["symbols"])
    assert "- pub struct `DatabasePool`" in joined
    assert "- impl `Drop for DatabasePool`" in joined
