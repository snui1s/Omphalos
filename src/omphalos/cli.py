# omphalos/cli.py
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import typer

from omphalos.cache import calculate_sha256, load_cache, save_cache
from omphalos.ignore import (
    IGNORE_FILE,
    NotAGitRepoError,
    collect_files,
    collect_git_files,
    ensure_ignore_file,
    load_ignore_spec,
)
from omphalos.parser import SUPPORTED_EXTENSIONS, extract_symbols
from omphalos.render import render_json, render_markdown

INDEX_FILE = "INDEX.md"
FORMATS = ("markdown", "json")

app = typer.Typer(help="Omphalos - codebase symbol index for LLMs")


def _package_version() -> str:
    """Read the installed package version (single source of truth: pyproject.toml)."""
    try:
        return version("omphalos")
    except PackageNotFoundError:
        return "unknown"


def _version_callback(value: bool):
    """Callback for --version flag to print the version and exit immediately."""
    if value:
        typer.echo(f"omph {_package_version()} (omphalos)")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True,
        help="Show version and exit.",
    )
):
    """Omphalos - Codebase symbol indexer for LLMs."""


@app.command()
def init(
    target_dir: str = typer.Argument(".", help="Target directory to initialize")
):
    """Create a default .omphignore file if not present in the target directory."""
    root = Path(target_dir).resolve()
    created = ensure_ignore_file(root)
    if created:
        typer.echo(f"Created {created.name}")
    else:
        typer.echo(f"Ignore file already exists ({IGNORE_FILE}).")


@app.command()
def scan(
    target_dir: str = typer.Argument(".", help="Target directory to scan"),
    output: Path = typer.Option(
        None, "--output", "-o",
        help=f"Index output path (default: {INDEX_FILE} in the target directory)",
    ),
    fmt: str = typer.Option(
        "markdown", "--format", help=f"Output format: {' or '.join(FORMATS)}"
    ),
    no_cache: bool = typer.Option(
        False, "--no-cache", help="Ignore cached symbols and re-parse every file"
    ),
    check: bool = typer.Option(
        False, "--check",
        help="Verify the index is up to date without writing; exit 1 if stale",
    ),
    git_only: bool = typer.Option(
        False, "--git-only", help="Only scan files tracked by git (requires a git repository)"
    ),
):
    """Scan multi-language codebase files and generate a symbol index with line numbers and docstrings."""
    root = Path(target_dir).resolve()
    if fmt not in FORMATS:
        typer.echo(f"error: invalid --format '{fmt}' (choose from {', '.join(FORMATS)})", err=True)
        raise typer.Exit(2)

    if not check:
        created = ensure_ignore_file(root)
        if created:
            typer.echo(f"Created default {created.name}")

    spec = load_ignore_spec(root)

    try:
        if git_only:
            target_files = collect_git_files(root, spec, SUPPORTED_EXTENSIONS)
        else:
            target_files = collect_files(root, spec, SUPPORTED_EXTENSIONS)
    except NotAGitRepoError as e:
        typer.echo(f"error: --git-only requires a git repository ({e})", err=True)
        raise typer.Exit(1) from e

    cache = {} if no_cache else load_cache(root)
    new_cache = {}
    files_data: dict[str, dict] = {}
    failed = 0

    with typer.progressbar(target_files, label="Indexing", file=sys.stderr) as progress:
        for file_path in progress:
            rel_posix = file_path.relative_to(root).as_posix()
            try:
                content = file_path.read_bytes()
            except OSError as e:
                typer.echo(f"error: cannot read {rel_posix}: {e}", err=True)
                failed += 1
                continue

            file_hash = calculate_sha256(content)
            # Check whether cached symbol data is reusable
            cached = cache.get(rel_posix)
            if cached and cached.get("hash") == file_hash and isinstance(cached.get("data"), dict):
                data = cached["data"]
            else:
                data = extract_symbols(file_path, content)

            new_cache[rel_posix] = {"hash": file_hash, "data": data}
            files_data[rel_posix] = data

            if data.get("error"):
                typer.echo(f"error: cannot parse {rel_posix}: {data['error']}", err=True)
                failed += 1

    renderer = render_json if fmt == "json" else render_markdown
    rendered = renderer(files_data)
    index_path = output if output else root / INDEX_FILE

    if check:
        existing = index_path.read_text(encoding="utf-8") if index_path.exists() else None
        if existing == rendered:
            typer.echo("Index is up to date.")
        else:
            typer.echo(f"Index is out of date: {index_path}", err=True)
            raise typer.Exit(1)
        return

    # Write index file and persist updated cache
    index_path.write_text(rendered, encoding="utf-8")
    save_cache(root, new_cache)
    summary = f"Updated {index_path.name} successfully ({len(target_files)} files scanned)."
    if failed:
        summary = f"Updated {index_path.name} ({len(target_files)} files scanned, {failed} failed)."
    typer.echo(summary)


if __name__ == "__main__":
    app()
