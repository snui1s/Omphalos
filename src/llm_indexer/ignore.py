# indexer/ignore.py
import os
from pathlib import Path
import pathspec

DEFAULT_IGNORES = [
    ".git/",
    ".llm_cache.json",
    ".llm_index",
    ".llm_ignore",
    ".llmignore",
    "llm_ignore",
    "__pycache__/",
    "node_modules/",
    ".venv/",
    "venv/",
    "dist/",
    "build/",
    "*.lock",
    "*.min.js",
]

IGNORE_TEMPLATE = """# .llm_ignore
# Files and directories to ignore when scanning codebase symbols.
# Uses gitignore pattern syntax.

# Version control & environments
.git/
.venv/
venv/
node_modules/

# Cache & build outputs
__pycache__/
dist/
build/
*.egg-info/

# Indexer cache & output
.llm_cache.json
.llm_index

# Locks & minified files
*.lock
*.min.js
"""

def ensure_ignore_file(root_dir: Path) -> Path | None:
    """สร้างไฟล์ .llm_ignore หากยังไม่มีไฟล์ ignore อยู่"""
    for filename in [".llm_ignore", ".llmignore", "llm_ignore"]:
        if (root_dir / filename).exists():
            return None

    target = root_dir / ".llm_ignore"
    target.write_text(IGNORE_TEMPLATE.strip() + "\n", encoding="utf-8")
    return target

def load_ignore_spec(root_dir: Path) -> pathspec.PathSpec:
    patterns = list(DEFAULT_IGNORES)

    # ลำดับสำคัญ: .llm_ignore อยู่หลัง .gitignore เพื่อให้ override ด้วย pattern เชิงลบได้
    for filename in [".gitignore", ".llm_ignore", ".llmignore", "llm_ignore"]:
        ignore_file = root_dir / filename
        if ignore_file.exists():
            patterns.extend(ignore_file.read_text(encoding="utf-8").splitlines())

    # GitIgnoreSpec เพื่อให้ semantics ตรงกับ git จริง เช่น การ negation (!pattern)
    return pathspec.GitIgnoreSpec.from_lines("gitignore", patterns)


def collect_files(
    root_dir: Path, spec: pathspec.PathSpec, supported_extensions: set[str]
) -> list[Path]:
    """เดินหาไฟล์ตามนามสกุลที่รองรับ โดยข้ามไฟล์/โฟลเดอร์ตาม ignore spec

    หมายเหตุ: โฟลเดอร์ที่ตรงกับ ignore spec จะถูกตัดทันที (prune) ซึ่งตรงกับ
    พฤติกรรมของ git — pattern เชิงลบ (!) ไม่สามารถ re-include ไฟล์ภายใน
    โฟลเดอร์ที่ถูก ignore ได้อยู่ดี
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