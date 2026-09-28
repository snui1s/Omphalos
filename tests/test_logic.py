# tests/test_logic.py
"""Internal-logic extraction: deduplicated call targets and raised exception types."""
from pathlib import Path

from typer.testing import CliRunner

from omphalos.cache import CACHE_FILE, CACHE_VERSION
from omphalos.cli import INDEX_FILE, app
from omphalos.parser import extract_symbols

runner = CliRunner()


def by_name(symbols, name):
    for s in symbols:
        if s["name"] == name:
            return s
        found = by_name(s.get("children", []), name)
        if found:
            return found
    return None


# ---------- Python ----------

def test_python_calls_and_raises():
    content = (
        b"def process(items):\n"                     # 1
        b"    validate(items)\n"                     # 2
        b"    validate(items)  # duplicate ignored\n"  # 3
        b"    obj = Helper(items)\n"                 # 4
        b"    try:\n"                                # 5
        b"        result = transform(obj)\n"         # 6
        b"    except ValueError:\n"                  # 7
        b"        raise\n"                           # 8
        b"    raise RuntimeError('bad')\n"           # 9
        b"    return result\n"                       # 10
    )
    fn = extract_symbols(Path("t.py"), content)["symbols"][0]
    assert fn["calls"] == ["validate", "Helper", "transform"]
    assert fn["raises"] == ["RuntimeError"]  # bare `raise` (re-raise) has no target


def test_python_plain_function_has_no_logic_keys():
    r = extract_symbols(Path("t.py"), b"def f():\n    pass\n")
    assert "calls" not in r["symbols"][0]
    assert "raises" not in r["symbols"][0]


def test_python_method_inside_class():
    content = (
        b"class Repo:\n"                       # 1
        b"    def save(self):\n"               # 2
        b"        self._flush()\n"             # 3
        b"        log.info('saved')\n"         # 4
        b"        raise IOError('disk')\n"     # 5
    )
    m = by_name(extract_symbols(Path("t.py"), content)["symbols"], "save")
    assert m["calls"] == ["self._flush", "log.info"]
    assert m["raises"] == ["IOError"]


def test_python_signature_and_decorator_calls_excluded():
    content = (
        b"@functools.cache\n"                                  # 1
        b"def scan(x=typer.Option(), y=Path('.')):\n"           # 2
        b"    p = file_path.relative_to(root).as_posix()\n"     # 3
        b"    h = hashlib.sha256(data).hexdigest()\n"           # 4
        b"    return p, h\n"                                    # 5
    )
    fn = by_name(extract_symbols(Path("t.py"), content)["symbols"], "scan")
    # signature/ decorator calls ต้องไม่ถูกนับ; chain ย่อเหลือทั้ง chain เรียบและ property ปลาย
    assert "typer.Option" not in fn["calls"]
    assert "functools.cache" not in fn["calls"]
    assert set(fn["calls"]) == {"file_path.relative_to", "as_posix", "hashlib.sha256", "hexdigest"}


# ---------- TypeScript / JavaScript ----------

def test_ts_function_calls_and_throws():
    content = (
        b"/** Does work. */\n"                            # 1
        b"export function doWork(input: string): string {\n"  # 2
        b"  validate(input);\n"                           # 3
        b"  const svc = new Service(input);\n"            # 4
        b"  if (!input) {\n"                              # 5
        b"    throw new Error('empty input');\n"          # 6
        b"  }\n"                                          # 7
        b"  return svc.run();\n"                          # 8
        b"}\n"                                            # 9
    )
    fn = extract_symbols(Path("t.ts"), content)["symbols"][0]
    assert fn["calls"] == ["validate", "Service", "svc.run"]
    assert fn["raises"] == ["Error"]


def test_ts_arrow_function_constant():
    content = b"export const logoutUser = () => {\n  api.post('/logout');\n  throw new AuthError('x');\n};\n"
    sym = extract_symbols(Path("t.ts"), content)["symbols"][0]
    assert sym["calls"] == ["api.post"]
    assert sym["raises"] == ["AuthError"]


# ---------- Go ----------

def test_go_calls_only_no_raises_semantics():
    content = (
        b"package bank\n\n"
        b"// OpenAccount creates an account.\n"     # 3
        b"func OpenAccount(name string) *Account {\n"  # 4
        b"    acct := NewAccount(name)\n"           # 5
        b"    log.Printf(\"created %s\", name)\n"   # 6
        b"    return acct\n"                        # 7
        b"}\n"                                      # 8
    )
    fn = by_name(extract_symbols(Path("t.go"), content)["symbols"], "OpenAccount")
    assert fn["calls"] == ["NewAccount", "log.Printf"]
    assert "raises" not in fn  # Go signals errors via return values, not throw statements


# ---------- Rust ----------

def test_rust_fn_calls():
    content = (
        b"/// Connects.\n"                          # 1
        b"pub fn connect(url: &str) -> Pool {\n"    # 2
        b"    let cfg = build_config(url);\n"       # 3
        b"    Pool::new(cfg)\n"                     # 4
        b"}\n"                                      # 5
    )
    fn = extract_symbols(Path("t.rs"), content)["symbols"][0]
    assert fn["calls"] == ["build_config", "Pool::new"]
    assert "raises" not in fn


def test_rust_impl_method_calls():
    content = (
        b"impl DatabasePool {\n"                    # 1
        b"    pub fn get_connection(&self) {\n"     # 2
        b"        self.lease();\n"                  # 3
        b"    }\n"                                  # 4
        b"}\n"                                      # 5
    )
    m = by_name(extract_symbols(Path("t.rs"), content)["symbols"], "get_connection")
    assert m["calls"] == ["self.lease"]


# ---------- Markdown / JSON rendering ----------

def test_markdown_renders_logic_inline():
    files_data = {
        "a.py": {"symbols": [{
            "kind": "function", "name": "process", "label": "`process()`",
            "line": 1, "doc": "", "exported": False, "children": [],
            "calls": ["validate", "transform"], "raises": ["RuntimeError"],
        }]},
    }
    from omphalos.render import render_markdown
    md = render_markdown(files_data)
    assert "- `process()` @1 (calls: `validate`, `transform`; raises: `RuntimeError`)" in md


def test_markdown_omits_logic_when_empty():
    files_data = {
        "a.py": {"symbols": [{
            "kind": "function", "name": "f", "label": "`f()`",
            "line": 1, "doc": "", "exported": False, "children": [],
        }]},
    }
    from omphalos.render import render_markdown
    assert "calls:" not in render_markdown(files_data)


def test_json_passes_logic_through(tmp_path: Path):
    (tmp_path / "m.py").write_text("def f():\n    g()\n    raise ValueError('x')\n", encoding="utf-8")
    out = tmp_path / "idx.json"
    result = runner.invoke(app, ["scan", str(tmp_path), "--format", "json", "-o", str(out)])
    assert result.exit_code == 0, result.output

    import json
    payload = json.loads(out.read_text(encoding="utf-8"))
    sym = payload["files"]["m.py"]["symbols"][0]
    assert sym["calls"] == ["g"]
    assert sym["raises"] == ["ValueError"]


def test_cli_scan_end_to_end_includes_logic(tmp_path: Path):
    (tmp_path / "m.py").write_text(
        "def handler(req):\n    auth.check(req)\n    raise PermissionError('no')\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0, result.output

    index = (tmp_path / INDEX_FILE).read_text(encoding="utf-8")
    assert "(calls: `auth.check`; raises: `PermissionError`)" in index

    import json
    cache = json.loads((tmp_path / CACHE_FILE).read_text(encoding="utf-8"))
    assert cache["version"] == CACHE_VERSION
    sym = cache["files"]["m.py"]["data"]["symbols"][0]
    assert sym["calls"] == ["auth.check"]
    assert sym["raises"] == ["PermissionError"]
