# tests/test_parser.py
from pathlib import Path

from omphalos.parser import extract_symbols


def by_name(symbols, name):
    for s in symbols:
        if s["name"] == name:
            return s
        found = by_name(s.get("children", []), name)
        if found:
            return found
    return None


def test_extract_python_structured():
    p = Path("unused.py")
    content = (
        b'class A:\n'          # 1
        b'    """Doc."""\n'    # 2
        b'    def m(self):\n'  # 3
        b'        pass\n\n'    # 4-5
        b'def f():\n'          # 6
        b'    pass\n'          # 7
    )
    syms = extract_symbols(p, content)["symbols"]
    assert len(syms) == 2

    cls = syms[0]
    assert cls["kind"] == "class"
    assert cls["name"] == "A"
    assert cls["label"] == "class `A`"
    assert cls["line"] == 1
    assert cls["doc"] == "Doc."
    assert cls["children"] == [{
        "kind": "method", "name": "m", "label": "`m()`", "line": 3,
        "doc": "", "exported": False, "children": [],
    }]

    fn = syms[1]
    assert fn["kind"] == "function"
    assert fn["label"] == "`f()`"
    assert fn["line"] == 6


def test_extract_python_decorated_uses_def_line():
    p = Path("unused.py")
    content = (
        b'@decorator\n'         # 1
        b'class A:\n'           # 2
        b'    pass\n'           # 3
    )
    syms = extract_symbols(p, content)["symbols"]
    assert syms[0]["line"] == 2


def test_extract_go_docs_and_lines():
    p = Path("unused.go")
    content = (
        b'// Account is a bank account.\n'        # 1
        b'type Account struct {\n'                # 2
        b'    balance int\n'                      # 3
        b'}\n\n'                                  # 4-5
        b'// Deposit adds amount.\n'              # 6
        b'func (a *Account) Deposit(n int) {}\n\n'  # 7-8
        b'//go:noinline\n'                        # 9
        b'// OpenAccount creates an account.\n'   # 10
        b'func OpenAccount() *Account {}\n'       # 11
    )
    syms = extract_symbols(p, content)["symbols"]

    acc = by_name(syms, "Account")
    assert acc["kind"] == "struct"
    assert acc["label"] == "type `Account` (struct)"
    assert acc["line"] == 2
    assert acc["doc"] == "Account is a bank account."

    dep = by_name(syms, "Deposit")
    assert dep["kind"] == "method"
    assert dep["label"] == "func `(a *Account) Deposit()`"
    assert dep["line"] == 7
    assert dep["doc"] == "Deposit adds amount."

    open_acc = by_name(syms, "OpenAccount")
    # //go:noinline เป็น directive ต้องถูกข้าม ใช้บรรทัด doc ถัดไป
    assert open_acc["doc"] == "OpenAccount creates an account."
    assert open_acc["line"] == 11


def test_extract_go_interface_and_plain_type():
    p = Path("unused.go")
    content = (
        b'type Reader interface {\n'  # 1
        b'    Read()\n'               # 2
        b'}\n\n'                      # 3-4
        b'type MyInt int\n'           # 5
    )
    syms = extract_symbols(p, content)["symbols"]
    assert by_name(syms, "Reader")["label"] == "type `Reader` (interface)"
    assert by_name(syms, "MyInt")["label"] == "type `MyInt`"
    assert by_name(syms, "MyInt")["kind"] == "type"


def test_extract_rust_docs_and_traits():
    p = Path("unused.rs")
    content = (
        b'/// A database pool.\n'                       # 1
        b'pub struct DatabasePool;\n\n'                 # 2-3
        b'/// Errors.\n'                                # 4
        b'pub enum DbError { E }\n\n'                   # 5-6
        b'/// Connects to the db.\n'                    # 7
        b'pub fn connect() {}\n\n'                      # 8-9
        b'impl DatabasePool {\n'                        # 10
        b'    /// Get a connection.\n'                  # 11
        b'    pub fn get_connection(&self) {}\n'        # 12
        b'}\n\n'                                        # 13-14
        b'impl Drop for DatabasePool {\n'               # 15
        b'    fn drop(&mut self) {}\n'                  # 16
        b'}\n'                                          # 17
    )
    syms = extract_symbols(p, content)["symbols"]

    pool = by_name(syms, "DatabasePool")
    assert pool["kind"] == "struct"
    assert pool["label"] == "pub struct `DatabasePool`"
    assert pool["line"] == 2
    assert pool["doc"] == "A database pool."

    enum = by_name(syms, "DbError")
    assert enum["label"] == "pub enum `DbError`"
    assert enum["line"] == 5

    connect = by_name(syms, "connect")
    assert connect["label"] == "pub fn `connect()`"
    assert connect["line"] == 8
    assert connect["doc"] == "Connects to the db."

    get_conn = by_name(syms, "get_connection")
    assert get_conn["label"] == "`pub fn get_connection()`"
    assert get_conn["line"] == 12
    assert get_conn["doc"] == "Get a connection."

    drop_impl = next(s for s in syms if s["kind"] == "impl" and "Drop" in s["name"])
    assert drop_impl["name"] == "Drop for DatabasePool"
    assert drop_impl["label"] == "impl `Drop for DatabasePool`"
    assert drop_impl["line"] == 15
    assert drop_impl["children"][0]["label"] == "`fn drop()`"


def test_extract_rust_trait():
    p = Path("unused.rs")
    content = b"/// A storage trait.\npub trait Storage {}\n"
    syms = extract_symbols(p, content)["symbols"]
    st = by_name(syms, "Storage")
    assert st["kind"] == "trait"
    assert st["label"] == "pub trait `Storage`"
    assert st["doc"] == "A storage trait."


def test_extract_ts_jsdoc_and_exports():
    p = Path("unused.ts")
    content = (
        b'/** Verify the token. */\n'                 # 1
        b'export function verifyToken() {}\n\n'       # 2-3
        b'/** Endpoint URL. */\n'                     # 4
        b'export const API_ENDPOINT = "/api";\n\n'    # 5-6
        b'/** Log out. */\n'                          # 7
        b'export const logoutUser = () => {};\n\n'    # 8-9
        b'/** Session manager. */\n'                  # 10
        b'export class SessionManager {\n'            # 11
        b'  /** Create a session. */\n'               # 12
        b'  createSession() {}\n'                     # 13
        b'}\n'                                        # 14
    )
    syms = extract_symbols(p, content)["symbols"]

    verify = by_name(syms, "verifyToken")
    assert verify["kind"] == "function"
    assert verify["label"] == "export function `verifyToken()`"
    assert verify["line"] == 2
    assert verify["doc"] == "Verify the token."
    assert verify["exported"] is True

    endpoint = by_name(syms, "API_ENDPOINT")
    assert endpoint["kind"] == "constant"
    assert endpoint["label"] == "export const `API_ENDPOINT`"
    assert endpoint["line"] == 5
    assert endpoint["exported"] is True

    logout = by_name(syms, "logoutUser")
    assert logout["label"] == "export const `logoutUser()`"

    cls = by_name(syms, "SessionManager")
    assert cls["label"] == "export class `SessionManager`"
    assert cls["line"] == 11
    assert cls["doc"] == "Session manager."
    method = cls["children"][0]
    assert method["label"] == "`createSession()`"
    assert method["line"] == 13
    assert method["doc"] == "Create a session."


def test_extract_ts_multiline_jsdoc_takes_first_line():
    p = Path("unused.ts")
    content = (
        b'/**\n'
        b' * Does something.\n'
        b' * More detail here.\n'
        b' */\n'
        b'export function doThing() {}\n'
    )
    syms = extract_symbols(p, content)["symbols"]
    assert syms[0]["doc"] == "Does something."
    assert syms[0]["line"] == 5


def test_extract_symbols_reads_file_when_no_content(tmp_path: Path):
    p = tmp_path / "m.py"
    p.write_text("def f():\n    pass\n", encoding="utf-8")
    syms = extract_symbols(p)["symbols"]
    assert by_name(syms, "f")["line"] == 1


def test_extract_symbols_empty_content(tmp_path: Path):
    assert extract_symbols(tmp_path / "e.py", b"") == {"symbols": []}


def test_extract_symbols_unknown_extension(tmp_path: Path):
    assert extract_symbols(tmp_path / "x.txt", b"anything") == {"symbols": []}


def test_extract_fixture_ts():
    fixture = Path(__file__).parent / "fixtures" / "sample.ts"
    syms = extract_symbols(fixture)["symbols"]
    iface = by_name(syms, "UserProfile")
    assert iface["kind"] == "interface"
    assert iface["exported"] is True
    assert by_name(syms, "verifyToken") is not None


def test_extract_fixture_go():
    fixture = Path(__file__).parent / "fixtures" / "sample.go"
    syms = extract_symbols(fixture)["symbols"]
    assert by_name(syms, "Account")["kind"] == "struct"
    assert by_name(syms, "Deposit") is not None


def test_extract_fixture_rust():
    fixture = Path(__file__).parent / "fixtures" / "sample.rs"
    syms = extract_symbols(fixture)["symbols"]
    assert by_name(syms, "DatabasePool")["label"] == "pub struct `DatabasePool`"
    assert any(s["kind"] == "impl" and "Drop" in s["name"] for s in syms)
