# omphalos/cli.py
import sys
import time
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
from omphalos.updater import notify_if_update_available
from omphalos.watcher import watch_loop

# Ensure UTF-8 output streams on all platforms (especially Windows cp1252)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

INDEX_FILE = "INDEX.md"
FORMATS = ("markdown", "json")

app = typer.Typer(
    add_completion=False,
)


def _package_version() -> str:
    """Read the installed package version (single source of truth: pyproject.toml)."""
    try:
        return version("omphalos")
    except PackageNotFoundError:
        return "unknown"


def _version_callback(value: bool):
    """Callback for --version flag to print the version and exit immediately."""
    if value:
        typer.echo(
            typer.style("omph ", fg=typer.colors.CYAN, bold=True)
            + typer.style(_package_version(), fg=typer.colors.GREEN, bold=True)
            + typer.style(" (omphalos)", fg=typer.colors.BRIGHT_BLACK)
        )
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True,
        help="Show version and exit.",
    )
):
    """Omphalos - Codebase symbol indexer for LLMs.

    Quick start:

      omph scan                  Scan repository and generate INDEX.md

      omph scan --watch          Watch for file changes and re-index automatically

      omph watch                 Shorthand to start watch mode

      omph scan --check          Verify index is up to date (exit 1 if stale)

      omph scan --git-only       Scan only files tracked by Git

      omph scan --format json    Export index as JSON

      omph init                  Create a default .omphignore file

    For full options of each command, run: omph COMMAND --help
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command()
def init(
    target_dir: str = typer.Argument(".", help="Target directory to initialize")
):
    """Create a default .omphignore file if not present in the target directory."""
    root = Path(target_dir).resolve()
    created = ensure_ignore_file(root)
    if created:
        typer.echo(
            typer.style("Created ", fg=typer.colors.GREEN, bold=True)
            + typer.style(created.name, fg=typer.colors.CYAN, bold=True)
        )
    else:
        typer.echo(typer.style(f"Ignore file already exists ({IGNORE_FILE}).", fg=typer.colors.BRIGHT_BLACK))
    notify_if_update_available(_package_version())


def _execute_scan(
    root: Path,
    output: Path | None = None,
    fmt: str = "markdown",
    no_cache: bool = False,
    git_only: bool = False,
    show_progress: bool = True,
) -> tuple[Path, int, int, int]:
    """Scan files, update index and cache, and return summary statistics."""
    spec = load_ignore_spec(root)
    if git_only:
        target_files = collect_git_files(root, spec, SUPPORTED_EXTENSIONS)
    else:
        target_files = collect_files(root, spec, SUPPORTED_EXTENSIONS)

    cache = {} if no_cache else load_cache(root)
    new_cache = {}
    files_data: dict[str, dict] = {}
    failed = 0
    reparsed = 0

    def _process_file(file_path: Path):
        nonlocal failed, reparsed
        rel_posix = file_path.relative_to(root).as_posix()
        try:
            content = file_path.read_bytes()
        except OSError as e:
            typer.echo(typer.style(f"error: cannot read {rel_posix}: {e}", fg=typer.colors.RED), err=True)
            failed += 1
            return

        file_hash = calculate_sha256(content)
        cached = cache.get(rel_posix)
        if cached and cached.get("hash") == file_hash and isinstance(cached.get("data"), dict):
            data = cached["data"]
        else:
            data = extract_symbols(file_path, content)
            reparsed += 1

        new_cache[rel_posix] = {"hash": file_hash, "data": data}
        files_data[rel_posix] = data

        if data.get("error"):
            typer.echo(typer.style(f"error: cannot parse {rel_posix}: {data['error']}", fg=typer.colors.RED), err=True)
            failed += 1

    if show_progress:
        with typer.progressbar(target_files, label="Indexing", file=sys.stderr) as progress:
            for file_path in progress:
                _process_file(file_path)
    else:
        for file_path in target_files:
            _process_file(file_path)

    renderer = render_json if fmt == "json" else render_markdown
    rendered = renderer(files_data)
    index_path = output if output else root / INDEX_FILE

    index_path.write_text(rendered, encoding="utf-8")
    save_cache(root, new_cache)
    return index_path, len(target_files), reparsed, failed


def _start_watcher(
    root: Path,
    index_path: Path,
    output: Path | None = None,
    fmt: str = "markdown",
    no_cache: bool = False,
    git_only: bool = False,
) -> None:
    """Watch codebase files for changes and re-index automatically."""
    typer.echo(
        typer.style("Watching ", fg=typer.colors.CYAN, bold=True)
        + typer.style(str(root), fg=typer.colors.WHITE, bold=True)
        + typer.style(" for changes... ", fg=typer.colors.CYAN)
        + typer.style("(Press Ctrl+C to stop)", fg=typer.colors.BRIGHT_BLACK)
    )

    def on_change(changes: list[Path]) -> None:
        now = time.strftime("%H:%M:%S")
        rel_names = []
        for p in changes:
            try:
                rel_names.append(p.relative_to(root).as_posix())
            except ValueError:
                rel_names.append(p.name)

        if len(rel_names) == 1:
            desc = rel_names[0]
        elif len(rel_names) <= 3:
            desc = ", ".join(rel_names)
        else:
            desc = f"{len(rel_names)} files"

        tag = typer.style(f"[{now}]", fg=typer.colors.BRIGHT_BLACK)
        action = typer.style(" Change detected in ", fg=typer.colors.YELLOW)
        target = typer.style(desc, fg=typer.colors.CYAN, bold=True)
        typer.echo(f"{tag}{action}{target}")

        try:
            _, _, reparsed, failed = _execute_scan(
                root=root,
                output=output,
                fmt=fmt,
                no_cache=no_cache,
                git_only=git_only,
                show_progress=False,
            )
            if failed:
                status = typer.style(f" Updated {index_path.name}", fg=typer.colors.YELLOW, bold=True)
                details = typer.style(f" ({reparsed} file(s) re-parsed, {failed} failed).", fg=typer.colors.RED)
            else:
                status = typer.style(f" Updated {index_path.name}", fg=typer.colors.GREEN, bold=True)
                details = typer.style(f" ({reparsed} file(s) re-parsed).", fg=typer.colors.BRIGHT_BLACK)
            typer.echo(f"{tag}{status}{details}")
        except Exception as e:
            typer.echo(f"{tag} " + typer.style(f"error during re-indexing: {e}", fg=typer.colors.RED), err=True)

    try:
        watch_loop(
            root=root,
            on_change=on_change,
            git_only=git_only,
        )
    except KeyboardInterrupt:
        typer.echo(typer.style("\nStopped watching.", fg=typer.colors.YELLOW))


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
    watch: bool = typer.Option(
        False, "--watch", "-w", help="Watch codebase files for changes and re-index automatically"
    ),
):
    """Scan multi-language codebase files and generate a symbol index with line numbers and docstrings."""
    root = Path(target_dir).resolve()
    if fmt not in FORMATS:
        typer.echo(
            typer.style(f"error: invalid --format '{fmt}' (choose from {', '.join(FORMATS)})", fg=typer.colors.RED),
            err=True,
        )
        raise typer.Exit(2)

    if check and watch:
        typer.echo(typer.style("error: --check cannot be used with --watch", fg=typer.colors.RED), err=True)
        raise typer.Exit(2)

    if not check:
        created = ensure_ignore_file(root)
        if created:
            typer.echo(
                typer.style("Created default ", fg=typer.colors.GREEN)
                + typer.style(created.name, fg=typer.colors.CYAN, bold=True)
            )

    if check:
        spec = load_ignore_spec(root)
        try:
            if git_only:
                target_files = collect_git_files(root, spec, SUPPORTED_EXTENSIONS)
            else:
                target_files = collect_files(root, spec, SUPPORTED_EXTENSIONS)
        except NotAGitRepoError as e:
            typer.echo(typer.style(f"error: --git-only requires a git repository ({e})", fg=typer.colors.RED), err=True)
            raise typer.Exit(1) from e

        cache = {} if no_cache else load_cache(root)
        files_data: dict[str, dict] = {}
        with typer.progressbar(target_files, label="Indexing", file=sys.stderr) as progress:
            for file_path in progress:
                rel_posix = file_path.relative_to(root).as_posix()
                try:
                    content = file_path.read_bytes()
                except OSError as e:
                    typer.echo(typer.style(f"error: cannot read {rel_posix}: {e}", fg=typer.colors.RED), err=True)
                    continue

                file_hash = calculate_sha256(content)
                cached = cache.get(rel_posix)
                if cached and cached.get("hash") == file_hash and isinstance(cached.get("data"), dict):
                    data = cached["data"]
                else:
                    data = extract_symbols(file_path, content)
                files_data[rel_posix] = data

        renderer = render_json if fmt == "json" else render_markdown
        rendered = renderer(files_data)
        index_path = output if output else root / INDEX_FILE
        existing = index_path.read_text(encoding="utf-8") if index_path.exists() else None
        if existing == rendered:
            typer.echo(typer.style("Index is up to date.", fg=typer.colors.GREEN, bold=True))
        else:
            typer.echo(typer.style(f"Index is out of date: {index_path}", fg=typer.colors.RED, bold=True), err=True)
            raise typer.Exit(1)
        return

    try:
        index_path, total_files, reparsed, failed = _execute_scan(
            root=root,
            output=output,
            fmt=fmt,
            no_cache=no_cache,
            git_only=git_only,
            show_progress=True,
        )
    except NotAGitRepoError as e:
        typer.echo(typer.style(f"error: --git-only requires a git repository ({e})", fg=typer.colors.RED), err=True)
        raise typer.Exit(1) from e

    if failed:
        status = typer.style(f"Updated {index_path.name}", fg=typer.colors.YELLOW, bold=True)
        details = typer.style(f" ({total_files} files scanned, {failed} failed).", fg=typer.colors.RED)
    else:
        status = typer.style(f"Updated {index_path.name} successfully", fg=typer.colors.GREEN, bold=True)
        details = typer.style(f" ({total_files} files scanned).", fg=typer.colors.BRIGHT_BLACK)
    typer.echo(status + details)

    notify_if_update_available(_package_version(), is_json=(fmt == "json"), is_check=check)

    if watch:
        _start_watcher(
            root=root,
            index_path=index_path,
            output=output,
            fmt=fmt,
            no_cache=no_cache,
            git_only=git_only,
        )


@app.command()
def watch(
    target_dir: str = typer.Argument(".", help="Target directory to watch and scan"),
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
    git_only: bool = typer.Option(
        False, "--git-only", help="Only scan files tracked by git (requires a git repository)"
    ),
):
    """Watch codebase files for changes and re-index automatically."""
    scan(
        target_dir=target_dir,
        output=output,
        fmt=fmt,
        no_cache=no_cache,
        check=False,
        git_only=git_only,
        watch=True,
    )


if __name__ == "__main__":
    app()

