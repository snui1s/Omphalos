# tests/test_edge_cases.py
"""Edge cases: binary/BOM/CRLF/unicode content, ชื่อไฟล์แปลก ๆ, ไฟล์ใหญ่, extension mapping"""
import json
from pathlib import Path

from typer.testing import CliRunner

from omphalos.cache import CACHE_FILE
from omphalos.cli import INDEX_FILE, app
from omphalos.parser import extract_symbols

runner = CliRunner()
FIXTURES = Path(__file__).parent / "fixtures"


def by_name(symbols, name):
    for s in symbols:
        if s["name"] == name:
            return s
        found = by_name(s.get("children", []), name)
        if found:
            return found
    return None


# ---------- content edge cases (parser level) ----------

def test_bom_prefix_does_not_shift_line_numbers():
    r = extract_symbols(Path("t.py"), b"\xef\xbb\xbf" + b'class A:\n    pass\n')
    assert r["symbols"][0]["name"] == "A"
    assert r["symbols"][0]["line"] == 1


def test_binary_garbage_with_supported_extension():
    r = extract_symbols(Path("t.py"), bytes(range(256)) * 4)
    assert r.get("error") is None
    assert r["symbols"] == []


def test_null_bytes_inside_file():
    r = extract_symbols(Path("t.py"), b"def f():\n\x00\x00\xff\xfe\n    pass\n")
    assert r.get("error") is None
    assert isinstance(r["symbols"], list)


def test_crlf_line_endings_keep_line_numbers():
    r = extract_symbols(Path("t.py"), b"class A:\r\n    def m(self):\r\n        pass\r\n")
    cls = r["symbols"][0]
    assert cls["line"] == 1
    assert cls["children"][0]["name"] == "m"
    assert cls["children"][0]["line"] == 2


def test_thai_identifiers_and_docstrings():
    content = (
        "def top_level(สวัสดี: str) -> str:\n"
        '    """ฟังก์ชันที่มีชื่อพารามิเตอร์เป็นภาษาไทย."""\n'
        "    return สวัสดี\n"
    ).encode()
    r = extract_symbols(Path("t.py"), content)
    fn = r["symbols"][0]
    assert fn["name"] == "top_level"
    assert fn["doc"] == "ฟังก์ชันที่มีชื่อพารามิเตอร์เป็นภาษาไทย."


def test_large_file_parses_correctly():
    n = 3000
    content = b"".join(f"def fn{i}():\n    pass\n\n".encode() for i in range(n))
    syms = extract_symbols(Path("t.py"), content)["symbols"]
    assert len(syms) == n
    assert syms[0]["line"] == 1
    assert syms[-1]["line"] == 3 * (n - 1) + 1


def test_comment_only_file():
    r = extract_symbols(Path("t.py"), b"# just a comment\n# another\n")
    assert r["symbols"] == []


def test_file_with_only_blank_lines():
    assert extract_symbols(Path("t.py"), b"\n\n\n") == {"symbols": []}


# ---------- extension mapping ----------

def test_jsx_uses_tsx_parser_with_jsx_syntax():
    r = extract_symbols(
        Path("t.jsx"), b"export function Card() {\n  return <div>hi</div>;\n}\n"
    )
    assert r["symbols"][0]["name"] == "Card"
    assert r["symbols"][0]["exported"] is True


def test_mjs_and_cjs_map_to_javascript():
    for ext in (".mjs", ".cjs"):
        r = extract_symbols(Path(f"t{ext}"), b"export const run = async () => {};\n")
        assert r["symbols"][0]["name"] == "run"


# ---------- fixtures ----------

def test_fixture_sample_python():
    syms = extract_symbols(FIXTURES / "sample.py")["symbols"]
    # decorator: ใช้บรรทัดของ def ไม่ใช่บรรทัดของ @decorator
    assert by_name(syms, "cached_fn")["line"] == 7
    assert by_name(syms, "cached_fn")["doc"] == "Compute something expensive."

    greeter = by_name(syms, "Greeter")
    assert greeter["line"] == 12
    assert greeter["doc"] == "Greets people in various languages."
    assert [c["name"] for c in greeter["children"]] == ["greet", "fetch_greetings"]
    assert greeter["children"][0]["line"] == 15

    assert by_name(syms, "top_level")["line"] == 23


def test_fixture_sample_tsx():
    syms = extract_symbols(FIXTURES / "sample.tsx")["symbols"]
    props = by_name(syms, "AvatarProps")
    assert props["kind"] == "interface"
    assert props["line"] == 4
    assert props["doc"] == "Props for the avatar component."

    avatar = by_name(syms, "Avatar")
    assert avatar["kind"] == "function"
    assert avatar["line"] == 10

    lst = by_name(syms, "AvatarList")
    assert lst["label"] == "export const `AvatarList()`"
    assert lst["line"] == 14


def test_fixture_sample_js():
    syms = extract_symbols(FIXTURES / "sample.js")["symbols"]
    counter = by_name(syms, "createCounter")
    assert counter["doc"] == "Creates a counter closure."
    assert counter["exported"] is True

    helper = by_name(syms, "internalHelper")
    assert helper["label"] == "const `internalHelper()`"
    assert helper["exported"] is False


# ---------- CLI-level edge cases ----------

def test_scan_unicode_and_spaces_in_filename(tmp_path: Path):
    (tmp_path / "โค้ด ทดสอบ.py").write_text("def f():\n    pass\n", encoding="utf-8")
    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0, result.output

    index = (tmp_path / INDEX_FILE).read_text(encoding="utf-8")
    assert "## โค้ด ทดสอบ.py" in index

    cache = json.loads((tmp_path / CACHE_FILE).read_text(encoding="utf-8"))
    assert "โค้ด ทดสอบ.py" in cache["files"]


def test_scan_directory_with_no_supported_files(tmp_path: Path):
    (tmp_path / "readme.txt").write_text("nothing here", encoding="utf-8")
    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0, result.output

    index = (tmp_path / INDEX_FILE).read_text(encoding="utf-8")
    assert index.startswith("# Codebase Symbol Index")
    assert "##" not in index
    assert "0 files scanned" in result.output


def test_scan_deeply_nested_files(tmp_path: Path):
    deep = tmp_path
    for i in range(10):
        deep = deep / f"level{i}"
    deep.mkdir(parents=True)
    (deep / "leaf.py").write_text("def leaf():\n    pass\n", encoding="utf-8")

    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0, result.output
    rel = f"{'/'.join(f'level{i}' for i in range(10))}/leaf.py"
    assert f"## {rel}" in (tmp_path / INDEX_FILE).read_text(encoding="utf-8")
