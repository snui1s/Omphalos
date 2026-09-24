# omphalos/parser.py
from pathlib import Path
from typing import Any

import tree_sitter as ts
import tree_sitter_go as tsgo
import tree_sitter_javascript as tsjs
import tree_sitter_python as tspython
import tree_sitter_rust as tsrust
import tree_sitter_typescript as tsts

# Initialize Languages
_LANG_PYTHON = ts.Language(tspython.language())
_LANG_TS = ts.Language(tsts.language_typescript())
_LANG_TSX = ts.Language(tsts.language_tsx())
_LANG_JS = ts.Language(tsjs.language())
_LANG_GO = ts.Language(tsgo.language())
_LANG_RUST = ts.Language(tsrust.language())

# Parsers
_PARSER_PYTHON = ts.Parser(_LANG_PYTHON)
_PARSER_TS = ts.Parser(_LANG_TS)
_PARSER_TSX = ts.Parser(_LANG_TSX)
_PARSER_JS = ts.Parser(_LANG_JS)
_PARSER_GO = ts.Parser(_LANG_GO)
_PARSER_RUST = ts.Parser(_LANG_RUST)

SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "tsx",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".go": "go",
    ".rs": "rust",
}


def _text(node: ts.Node) -> str:
    """Decode Tree-sitter AST node text bytes to a UTF-8 string."""
    return (node.text or b"").decode("utf-8", errors="replace")


def _mk_symbol(kind: str, name: str, node: ts.Node, label: str, doc: str = "") -> dict[str, Any]:
    """Create a standardized symbol schema dictionary.
    
    Args:
        kind: Type of symbol (e.g., function, class, method, struct, interface).
        name: Identifier name of the symbol.
        node: Originating Tree-sitter AST node for extracting 1-indexed start line.
        label: Human/LLM-readable display label.
        doc: First-line summary or docstring (if available).
    """
    return {
        "kind": kind,
        "name": name,
        "label": label,
        "line": node.start_point[0] + 1,
        "doc": doc,
        "exported": False,
        "children": [],
    }


def _prev_comment_block(node: ts.Node) -> list[ts.Node]:
    """Return contiguous comment nodes immediately preceding the node (in top-to-bottom order).

    Note: Certain grammars (like Rust) include the trailing newline in line_comment,
    causing end_point to fall on the next line. We strip trailing newlines before checking contiguity.
    """
    def content_end_row(c: ts.Node) -> int:
        text = c.text or b""
        return c.end_point[0] - (len(text) - len(text.rstrip(b"\r\n")))

    block = []
    cur = node.prev_named_sibling
    row = node.start_point[0]
    while cur is not None and cur.type in ("comment", "line_comment") and content_end_row(cur) == row - 1:
        block.append(cur)
        row = cur.start_point[0]
        cur = cur.prev_named_sibling
    block.reverse()
    return block


def _get_py_docstring(node: ts.Node) -> str:
    """Extract the first line of a Python function or class docstring, if present."""
    body = node.child_by_field_name("body")
    if body and len(body.named_children) > 0:
        first = body.named_children[0]
        if first.type == "expression_statement" and len(first.named_children) > 0:
            str_node = first.named_children[0]
            if str_node.type == "string":
                # Intentional charset strip: remove repeated quotes (""" or ''') and surrounding whitespace
                raw = _text(str_node).strip("\"' \n\r\t")  # noqa: B005
                return raw.splitlines()[0].strip() if raw else ""
    return ""


def _go_doc(node: ts.Node) -> str:
    """Go doc comment: first line of comment block attached above declaration (skipping //go: directives)."""
    for c in _prev_comment_block(node):
        t = _text(c).strip()
        if t.startswith("//go:"):
            continue
        return t.removeprefix("//").strip()
    return ""


def _rust_doc(node: ts.Node) -> str:
    """Rust doc comment: first line of /// comment block attached above an item."""
    for c in _prev_comment_block(node):
        t = _text(c).strip()
        if t.startswith("///"):
            line = t.removeprefix("///").strip()
            if line:
                return line
    return ""


def _ts_doc(node: ts.Node) -> str:
    """JSDoc comment: first line containing content within a /** ... */ block attached above declaration."""
    for c in _prev_comment_block(node):
        t = _text(c).strip()
        if not t.startswith("/**"):
            continue
        for raw in t.splitlines():
            line = raw.strip().removeprefix("/**").removeprefix("*").removesuffix("*/").strip()
            if line:
                return line
    return ""


def _unwrap_decorated(node: ts.Node) -> ts.Node:
    """Unwrap core definition node (function/class) from a Python decorated_definition."""
    if node.type == "decorated_definition":
        for child in node.named_children:
            if child.type in ("function_definition", "async_function_definition", "class_definition"):
                return child
    return node


def _extract_python(root_node: ts.Node) -> list[dict[str, Any]]:
    """Extract all symbols from a Python AST (classes, methods, functions)."""
    symbols = []
    for raw_node in root_node.children:
        node = _unwrap_decorated(raw_node)
        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = _text(name_node)
                cls = _mk_symbol("class", name, node, f"class `{name}`", _get_py_docstring(node))

                body = node.child_by_field_name("body")
                for child_raw in (body.named_children if body else []):
                    child = _unwrap_decorated(child_raw)
                    if child.type in ("function_definition", "async_function_definition"):
                        m_name_node = child.child_by_field_name("name")
                        if m_name_node:
                            m_name = _text(m_name_node)
                            cls["children"].append(_mk_symbol(
                                "method", m_name, child, f"`{m_name}()`", _get_py_docstring(child)))
                symbols.append(cls)

        elif node.type in ("function_definition", "async_function_definition"):
            name_node = node.child_by_field_name("name")
            if name_node:
                name = _text(name_node)
                symbols.append(_mk_symbol("function", name, node, f"`{name}()`", _get_py_docstring(node)))

    return symbols


def _ts_symbol(target: ts.Node, doc_node: ts.Node, exported: bool) -> dict[str, Any] | None:
    """Extract a structured symbol dictionary from a TypeScript/JavaScript declaration node."""
    prefix = "export " if exported else ""

    if target.type == "interface_declaration":
        name_node = target.child_by_field_name("name")
        if name_node:
            return _mk_symbol("interface", _text(name_node), target,
                              f"{prefix}interface `{_text(name_node)}`", _ts_doc(doc_node))

    elif target.type == "type_alias_declaration":
        name_node = target.child_by_field_name("name")
        if name_node:
            return _mk_symbol("type", _text(name_node), target,
                              f"{prefix}type `{_text(name_node)}`", _ts_doc(doc_node))

    elif target.type == "function_declaration":
        name_node = target.child_by_field_name("name")
        if name_node:
            return _mk_symbol("function", _text(name_node), target,
                              f"{prefix}function `{_text(name_node)}()`", _ts_doc(doc_node))

    elif target.type == "class_declaration":
        name_node = target.child_by_field_name("name")
        if name_node:
            cls = _mk_symbol("class", _text(name_node), target,
                             f"{prefix}class `{_text(name_node)}`", _ts_doc(doc_node))
            body = target.child_by_field_name("body")
            if body:
                for item in body.named_children:
                    if item.type == "method_definition":
                        m_name_node = item.child_by_field_name("name")
                        if m_name_node:
                            cls["children"].append(_mk_symbol(
                                "method", _text(m_name_node), item, f"`{_text(m_name_node)}()`", _ts_doc(item)))
            return cls

    elif target.type == "lexical_declaration":
        kind_word = _text(target.children[0]) if target.children else "const"
        kind = "constant" if kind_word == "const" else "variable"
        for decl in target.named_children:
            if decl.type == "variable_declarator":
                name_node = decl.child_by_field_name("name")
                value_node = decl.child_by_field_name("value")
                if name_node:
                    name = _text(name_node)
                    is_fn = value_node and value_node.type in ("arrow_function", "function_expression")
                    suffix = "()" if is_fn else ""
                    return _mk_symbol(kind, name, target, f"{prefix}{kind_word} `{name}{suffix}`", _ts_doc(doc_node))

    return None


def _extract_ts_js(root_node: ts.Node) -> list[dict[str, Any]]:
    """Extract symbols from TypeScript and JavaScript ASTs (functions, classes, interfaces, types, exports)."""
    symbols = []
    for node in root_node.children:
        exported = False
        target = node

        if node.type == "export_statement":
            exported = True
            named = [c for c in node.named_children if c.type not in ("comment",)]
            if named:
                target = named[0]

        # Doc comment is attached above export_statement (or declaration itself if not exported)
        sym = _ts_symbol(target, node, exported)
        if sym:
            sym["exported"] = exported
            symbols.append(sym)

    return symbols


def _extract_go(root_node: ts.Node) -> list[dict[str, Any]]:
    """Extract symbols from Go AST (types, structs, interfaces, functions, methods with receivers)."""
    symbols = []
    for node in root_node.children:
        if node.type == "type_declaration":
            specs = [c for c in node.named_children if c.type == "type_spec"]
            for spec in specs:
                name_node = spec.child_by_field_name("name")
                type_val = spec.child_by_field_name("type")
                if not name_node or type_val is None:
                    continue
                t_kind = {"struct_type": "struct", "interface_type": "interface"}.get(type_val.type, "type")
                suffix = {"struct": " (struct)", "interface": " (interface)"}.get(t_kind, "")
                name = _text(name_node)
                # Grouped type block: doc comment sits above type_spec; single type: above type_declaration
                doc = _go_doc(spec)
                if not doc and len(specs) == 1:
                    doc = _go_doc(node)
                symbols.append(_mk_symbol(t_kind, name, spec, f"type `{name}`{suffix}", doc))

        elif node.type == "function_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = _text(name_node)
                symbols.append(_mk_symbol("function", name, node, f"func `{name}()`", _go_doc(node)))

        elif node.type == "method_declaration":
            recv = node.child_by_field_name("receiver")
            name_node = node.child_by_field_name("name")
            if name_node:
                name = _text(name_node)
                recv_str = _text(recv) if recv else ""
                symbols.append(_mk_symbol("method", name, node, f"func `{recv_str} {name}()`", _go_doc(node)))

    return symbols


def _rust_vis(node: ts.Node) -> str:
    """Extract visibility modifier string (e.g., 'pub') from a Rust item node."""
    for c in node.children:
        if c.type == "visibility_modifier":
            return _text(c)
    return ""


def _extract_rust(root_node: ts.Node) -> list[dict[str, Any]]:
    """Extract symbols from Rust AST (structs, enums, traits, functions, and impl blocks)."""
    symbols = []
    for node in root_node.children:
        vis = _rust_vis(node)
        vis_str = f"{vis} " if vis else ""

        if node.type == "struct_item":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = _text(name_node)
                symbols.append(_mk_symbol("struct", name, node, f"{vis_str}struct `{name}`", _rust_doc(node)))

        elif node.type == "enum_item":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = _text(name_node)
                symbols.append(_mk_symbol("enum", name, node, f"{vis_str}enum `{name}`", _rust_doc(node)))

        elif node.type == "trait_item":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = _text(name_node)
                symbols.append(_mk_symbol("trait", name, node, f"{vis_str}trait `{name}`", _rust_doc(node)))

        elif node.type == "function_item":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = _text(name_node)
                symbols.append(_mk_symbol("function", name, node, f"{vis_str}fn `{name}()`", _rust_doc(node)))

        elif node.type == "impl_item":
            trait_node = node.child_by_field_name("trait")
            type_node = node.child_by_field_name("type")
            impl_header = ""
            if trait_node and type_node:
                impl_header = f"{_text(trait_node)} for {_text(type_node)}"
            elif type_node:
                impl_header = _text(type_node)

            if impl_header:
                impl = _mk_symbol("impl", impl_header, node, f"impl `{impl_header}`", _rust_doc(node))
                body = node.child_by_field_name("body")
                if body:
                    for item in body.named_children:
                        if item.type == "function_item":
                            m_vis = _rust_vis(item)
                            m_vis_str = f"{m_vis} " if m_vis else ""
                            m_name_node = item.child_by_field_name("name")
                            if m_name_node:
                                m_name = _text(m_name_node)
                                impl["children"].append(_mk_symbol(
                                    "method", m_name, item, f"`{m_vis_str}fn {m_name}()`", _rust_doc(item)))
                symbols.append(impl)

    return symbols


def extract_symbols(file_path: Path, content: bytes | None = None) -> dict[str, Any]:
    """Parse file content using the appropriate Tree-sitter language grammar and extract code symbols.
    
    Args:
        file_path: Path to the target source file (used for extension detection and reading content if not given).
        content: Optional raw bytes content of the file.
        
    Returns:
        Dictionary containing extracted symbols or an error message if parsing fails.
    """
    ext = file_path.suffix.lower()
    lang_type = SUPPORTED_EXTENSIONS.get(ext)
    if not lang_type:
        return {"symbols": []}

    if content is None:
        try:
            content = file_path.read_bytes()
        except Exception as e:
            return {"error": str(e), "symbols": []}

    try:
        if lang_type == "python":
            tree = _PARSER_PYTHON.parse(content)
            symbols = _extract_python(tree.root_node)
        elif lang_type == "typescript":
            tree = _PARSER_TS.parse(content)
            symbols = _extract_ts_js(tree.root_node)
        elif lang_type == "tsx":
            tree = _PARSER_TSX.parse(content)
            symbols = _extract_ts_js(tree.root_node)
        elif lang_type == "javascript":
            tree = _PARSER_JS.parse(content)
            symbols = _extract_ts_js(tree.root_node)
        elif lang_type == "go":
            tree = _PARSER_GO.parse(content)
            symbols = _extract_go(tree.root_node)
        elif lang_type == "rust":
            tree = _PARSER_RUST.parse(content)
            symbols = _extract_rust(tree.root_node)
        else:
            symbols = []
    except Exception as e:
        return {"error": str(e), "symbols": []}

    return {"symbols": symbols}
