# indexer/cli.py
from pathlib import Path
import typer
from llm_indexer.ignore import load_ignore_spec, ensure_ignore_file, collect_files
from llm_indexer.cache import calculate_sha256, load_cache, save_cache
from llm_indexer.parser import extract_symbols, SUPPORTED_EXTENSIONS

app = typer.Typer(help="LLM Indexer - Codebase symbol indexer for LLMs")

@app.callback()
def callback():
    """LLM Indexer CLI"""
    pass

@app.command()
def init(
    target_dir: str = typer.Argument(".", help="Target directory to initialize")
):
    """Create a default .llm_ignore file if not present."""
    root = Path(target_dir).resolve()
    created = ensure_ignore_file(root)
    if created:
        typer.echo(f"Created {created.name}")
    else:
        typer.echo("Ignore file already exists (.llm_ignore).")

@app.command()
def scan(
    target_dir: str = typer.Argument(".", help="Target directory to scan")
):
    """Scan multi-language files and generate codebase symbol index."""
    root = Path(target_dir).resolve()
    created = ensure_ignore_file(root)
    if created:
        typer.echo(f"Created default {created.name}")

    spec = load_ignore_spec(root)
    cache = load_cache(root)
    new_cache = {}

    index_lines = ["# Codebase Symbol Index\n"]
    target_files = collect_files(root, spec, SUPPORTED_EXTENSIONS)

    failed = 0
    for file_path in target_files:
        rel_posix = file_path.relative_to(root).as_posix()
        try:
            content = file_path.read_bytes()
        except OSError as e:
            typer.echo(f"error: cannot read {rel_posix}: {e}", err=True)
            failed += 1
            continue

        file_hash = calculate_sha256(content)
        # ตรวจสอบว่าดึงจาก Cache ได้หรือไม่
        cached = cache.get(rel_posix)
        if cached and cached.get("hash") == file_hash and isinstance(cached.get("data"), dict):
            data = cached["data"]
        else:
            data = extract_symbols(file_path, content)

        new_cache[rel_posix] = {"hash": file_hash, "data": data}

        if data.get("error"):
            typer.echo(f"error: cannot parse {rel_posix}: {data['error']}", err=True)
            failed += 1

        symbols = data.get("symbols", [])
        if symbols:
            index_lines.append(f"## {rel_posix}")
            index_lines.extend(symbols)
            index_lines.append("")

    # บันทึกไฟล์สารบัญและ Cache
    (root / ".llm_index").write_text("\n".join(index_lines), encoding="utf-8")
    save_cache(root, new_cache)
    if failed:
        typer.echo(f"Updated .llm_index ({len(target_files)} files scanned, {failed} failed).")
    else:
        typer.echo(f"Updated .llm_index successfully ({len(target_files)} files scanned).")

if __name__ == "__main__":
    app()