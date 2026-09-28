# omphalos/ignore.py
import os
import subprocess
from collections.abc import Container
from pathlib import Path

import pathspec

DEFAULT_IGNORES = [
    ".git/",
    ".omphcache",
    ".omphalos_cache.json",
    "INDEX.md",
    ".omphalos_index",
    ".omphignore",
    ".omphalos_ignore",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    "node_modules/",
    ".venv/",
    "venv/",
    "dist/",
    "build/",
    "*.lock",
    "*.min.js",
]

IGNORE_TEMPLATE = """# .omphignore
# Files and directories to ignore when scanning codebase symbols.
# Uses gitignore pattern syntax.

# Version control & environments
.git/
.venv/
venv/
node_modules/

# Cache & build outputs
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
dist/
build/
*.egg-info/

# Omphalos cache & output
.omphcache
INDEX.md

# Locks & minified files
*.lock
*.min.js
"""

IGNORE_FILE = ".omphignore"

def ensure_ignore_file(root_dir: Path) -> Path | None:
    """Create a default .omphignore file if it does not already exist.

    Returns:
        Path of the newly created ignore file, or None if it already exists.
    """
    target = root_dir / IGNORE_FILE
    if target.exists():
        return None

    target.write_text(IGNORE_TEMPLATE.strip() + "\n", encoding="utf-8")
    return target

def load_ignore_spec(root_dir: Path) -> pathspec.PathSpec:
    """Load and merge all ignore rules into a unified PathSpec.

    Precedence order:
    1. DEFAULT_IGNORES (e.g., .git, venv, caches)
    2. Rules from .gitignore (if present)
    3. Rules from .omphignore (and legacy .omphalos_ignore if present)

    Returns:
        GitIgnoreSpec matcher for filtering paths.
    """
    patterns = list(DEFAULT_IGNORES)

    # Order matters: ignore files come after .gitignore to allow overriding with negation patterns
    for filename in [".gitignore", ".omphalos_ignore", IGNORE_FILE]:
        ignore_file = root_dir / filename
        if ignore_file.exists():
            patterns.extend(ignore_file.read_text(encoding="utf-8").splitlines())

    # Use GitIgnoreSpec for git-compliant semantics (negation, directory matching)
    return pathspec.GitIgnoreSpec.from_lines("gitignore", patterns)


def collect_files(
    root_dir: Path, spec: pathspec.PathSpec, supported_extensions: Container[str]
) -> list[Path]:
    """Recursively collect supported files, pruning directories matched by ignore spec.

    Note: Directories matching ignore rules are pruned immediately during os.walk,
    matching git behavior (negation patterns cannot re-include files within an
    ignored directory).
    """
    target_files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        rel_dir = Path(dirpath).relative_to(root_dir)
        dirnames[:] = [
            d for d in dirnames
            if not spec.match_file(f"{(rel_dir / d).as_posix()}/")
        ]
        for f in filenames:
            p = Path(f)
            if p.suffix.lower() in supported_extensions:
                rel_file = (rel_dir / f).as_posix()
                if not spec.match_file(rel_file):
                    target_files.append(root_dir / rel_file)

    target_files.sort()
    return target_files


class NotAGitRepoError(Exception):
    pass


def collect_git_files(
    root_dir: Path, spec: pathspec.PathSpec, supported_extensions: Container[str]
) -> list[Path]:
    """Collect only files tracked by Git (via git ls-files), filtered by spec and extension.

    Args:
        root_dir: Root directory of the Git repository.
        spec: PathSpec ignore filter.
        supported_extensions: Collection of supported file extensions.

    Returns:
        List of matching file Paths that exist in the working tree.

    Raises:
        NotAGitRepoError: If root_dir is not inside a git repository or git binary is missing.
    """
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-z"], cwd=root_dir,
            capture_output=True, check=False,
        )
    except FileNotFoundError as e:
        raise NotAGitRepoError("git command not found") from e
    if proc.returncode != 0:
        msg = proc.stderr.decode("utf-8", errors="replace").strip()
        raise NotAGitRepoError(msg or "not a git repository")

    target_files: list[Path] = []
    for chunk in proc.stdout.split(b"\0"):
        if not chunk:
            continue
        rel = chunk.decode("utf-8", errors="replace").replace("\\", "/")
        p = Path(rel)
        if p.suffix.lower() not in supported_extensions:
            continue
        if not (root_dir / p).is_file():
            continue  # Present in git index but deleted from working tree
        if not spec.match_file(rel):
            target_files.append(root_dir / p)

    target_files.sort()
    return target_files
