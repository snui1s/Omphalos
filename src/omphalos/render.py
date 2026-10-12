# omphalos/render.py
"""Render structured symbol data (from parser/cache) into target output formats."""
import json
from typing import Any


def render_markdown(files_data: dict[str, dict[str, Any]], include_calls: bool = True) -> str:
    """Render structured symbol data into Markdown format for LLM context or human reading.

    Args:
        files_data: Symbol mapping keyed by relative file paths.
        include_calls: Emit the `calls:` annotation (roughly halves index size when False).

    Returns:
        Formatted Markdown index grouping symbols under file headers.
    """
    lines = ["# Codebase Symbol Index\n"]
    for path, data in files_data.items():
        symbols = data.get("symbols", [])
        if not symbols:
            continue
        lines.append(f"## {path}")
        _render_md_symbols(symbols, depth=0, lines=lines, include_calls=include_calls)
        lines.append("")
    return "\n".join(lines)


def _render_md_symbols(symbols: list[dict[str, Any]], depth: int, lines: list[str], include_calls: bool = True):
    """Recursively render symbols as nested Markdown bullet points.

    Includes label, @line number, docstring summary, and nested child symbols
    (such as methods within classes or trait implementations).
    """
    for sym in symbols:
        text = f"{'  ' * depth}- {sym['label']}"
        if sym.get("line"):
            text += f" @{sym['line']}"
        if sym.get("doc"):
            text += f": {sym['doc']}"
        # Internal logic detail: deduplicated call targets and raised exceptions (inline, keeps tree flat)
        detail = []
        if include_calls and sym.get("calls"):
            detail.append("calls: " + ", ".join(f"`{c}`" for c in sym["calls"]))
        if sym.get("raises"):
            detail.append("raises: " + ", ".join(f"`{r}`" for r in sym["raises"]))
        if detail:
            text += f" ({'; '.join(detail)})"
        lines.append(text)
        _render_md_symbols(sym.get("children", []), depth + 1, lines, include_calls)


def _without_calls(symbols: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a copy of the symbol tree with every `calls` key removed (input is not mutated)."""
    stripped = []
    for sym in symbols:
        copy = {k: v for k, v in sym.items() if k != "calls"}
        if sym.get("children"):
            copy["children"] = _without_calls(sym["children"])
        stripped.append(copy)
    return stripped


def render_json(files_data: dict[str, dict[str, Any]], include_calls: bool = True) -> str:
    """Render structured symbol data into a JSON string for programmatic consumption.

    Args:
        files_data: Symbol mapping keyed by relative file paths.
        include_calls: Keep the `calls` field on function-like symbols.

    Returns:
        Indented JSON string conforming to the Omphalos schema format.
    """
    payload = {
        "tool": "omphalos",
        "format_version": 1,
        "files": {
            path: {"symbols": data.get("symbols", []) if include_calls else _without_calls(data["symbols"])}
            for path, data in files_data.items()
            if data.get("symbols")
        },
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)
