# indexer/parser.py
from pathlib import Path
from typing import Any
import tree_sitter as ts
import tree_sitter_python as tspython
import tree_sitter_typescript as tsts
import tree_sitter_javascript as tsjs
import tree_sitter_go as tsgo
import tree_sitter_rust as tsrust

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


def _get_py_docstring(node: ts.Node) -> str:
    body = node.child_by_field_name("body")
    if body and len(body.named_children) > 0:
        first = body.named_children[0]
        if first.type == "expression_statement" and len(first.named_children) > 0:
            str_node = first.named_children[0]
            if str_node.type == "string":
                raw = str_node.text.decode("utf-8", errors="replace").strip('"""\'\'\' \n\r\t')
                return raw.splitlines()[0].strip() if raw else ""
    return ""


def _unwrap_decorated(node: ts.Node) -> ts.Node:
    if node.type == "decorated_definition":
        for child in node.named_children:
            if child.type in ("function_definition", "async_function_definition", "class_definition"):
                return child
    return node


def _extract_python(root_node: ts.Node) -> list[str]:
    lines = []
    for raw_node in root_node.children:
        node = _unwrap_decorated(raw_node)
        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8", errors="replace")
                doc = _get_py_docstring(node)
                desc = f": {doc}" if doc else ""
                lines.append(f"- class `{name}`{desc}")

                body = node.child_by_field_name("body")
                for child_raw in (body.named_children if body else []):
                    child = _unwrap_decorated(child_raw)
                    if child.type in ("function_definition", "async_function_definition"):
                        m_name_node = child.child_by_field_name("name")
                        if m_name_node:
                            m_name = m_name_node.text.decode("utf-8", errors="replace")
                            m_doc = _get_py_docstring(child)
                            m_desc = f": {m_doc}" if m_doc else ""
                            lines.append(f"  - `{m_name}()`{m_desc}")

        elif node.type in ("function_definition", "async_function_definition"):
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8", errors="replace")
                doc = _get_py_docstring(node)
                desc = f": {doc}" if doc else ""
                lines.append(f"- `{name}()`{desc}")

    return lines


def _extract_ts_js(root_node: ts.Node) -> list[str]:
    lines = []
    for node in root_node.children:
        is_exported = False
        target = node

        if node.type == "export_statement":
            is_exported = True
            named = [c for c in node.named_children if c.type not in ("comment",)]
            if named:
                target = named[0]

        prefix = "export " if is_exported else ""

        if target.type == "interface_declaration":
            name_node = target.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8", errors="replace")
                lines.append(f"- {prefix}interface `{name}`")

        elif target.type == "type_alias_declaration":
            name_node = target.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8", errors="replace")
                lines.append(f"- {prefix}type `{name}`")

        elif target.type == "function_declaration":
            name_node = target.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8", errors="replace")
                lines.append(f"- {prefix}function `{name}()`")

        elif target.type == "class_declaration":
            name_node = target.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8", errors="replace")
                lines.append(f"- {prefix}class `{name}`")
                body = target.child_by_field_name("body")
                if body:
                    for item in body.named_children:
                        if item.type == "method_definition":
                            m_name_node = item.child_by_field_name("name")
                            if m_name_node:
                                m_name = m_name_node.text.decode("utf-8", errors="replace")
                                lines.append(f"  - `{m_name}()`")

        elif target.type == "lexical_declaration":
            kind = target.children[0].text.decode("utf-8", errors="replace") if target.children else "const"
            for decl in target.named_children:
                if decl.type == "variable_declarator":
                    name_node = decl.child_by_field_name("name")
                    value_node = decl.child_by_field_name("value")
                    if name_node:
                        name = name_node.text.decode("utf-8", errors="replace")
                        is_fn = value_node and value_node.type in ("arrow_function", "function_expression")
                        suffix = "()" if is_fn else ""
                        lines.append(f"- {prefix}{kind} `{name}{suffix}`")

    return lines


def _extract_go(root_node: ts.Node) -> list[str]:
    lines = []
    for node in root_node.children:
        if node.type == "type_declaration":
            for spec in node.named_children:
                if spec.type == "type_spec":
                    name_node = spec.child_by_field_name("name")
                    type_val = spec.child_by_field_name("type")
                    t_kind = ""
                    if type_val:
                        if type_val.type == "struct_type":
                            t_kind = " (struct)"
                        elif type_val.type == "interface_type":
                            t_kind = " (interface)"
                    if name_node:
                        name = name_node.text.decode("utf-8", errors="replace")
                        lines.append(f"- type `{name}`{t_kind}")

        elif node.type == "function_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8", errors="replace")
                lines.append(f"- func `{name}()`")

        elif node.type == "method_declaration":
            recv = node.child_by_field_name("receiver")
            name_node = node.child_by_field_name("name")
            recv_str = recv.text.decode("utf-8", errors="replace") if recv else ""
            if name_node:
                name = name_node.text.decode("utf-8", errors="replace")
                lines.append(f"- func `{recv_str} {name}()`")

    return lines


def _extract_rust(root_node: ts.Node) -> list[str]:
    lines = []
    for node in root_node.children:
        vis = [c for c in node.children if c.type == "visibility_modifier"]
        vis_str = (vis[0].text.decode("utf-8", errors="replace") + " ") if vis else ""

        if node.type == "struct_item":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8", errors="replace")
                lines.append(f"- {vis_str}struct `{name}`")

        elif node.type == "enum_item":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8", errors="replace")
                lines.append(f"- {vis_str}enum `{name}`")

        elif node.type == "function_item":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf-8", errors="replace")
                lines.append(f"- {vis_str}fn `{name}()`")

        elif node.type == "impl_item":
            trait_node = node.child_by_field_name("trait")
            type_node = node.child_by_field_name("type")
            impl_header = ""
            if trait_node and type_node:
                impl_header = f"impl `{trait_node.text.decode('utf-8', errors='replace')} for {type_node.text.decode('utf-8', errors='replace')}`"
            elif type_node:
                impl_header = f"impl `{type_node.text.decode('utf-8', errors='replace')}`"

            if impl_header:
                lines.append(f"- {impl_header}")
                body = node.child_by_field_name("body")
                if body:
                    for item in body.named_children:
                        if item.type == "function_item":
                            m_vis = [c for c in item.children if c.type == "visibility_modifier"]
                            m_vis_str = (m_vis[0].text.decode("utf-8", errors="replace") + " ") if m_vis else ""
                            m_name_node = item.child_by_field_name("name")
                            if m_name_node:
                                m_name = m_name_node.text.decode("utf-8", errors="replace")
                                lines.append(f"  - `{m_vis_str}fn {m_name}()`")

    return lines


def extract_symbols(file_path: Path, content: bytes | None = None) -> dict[str, Any]:
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