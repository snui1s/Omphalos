# tests/test_ignore.py
import shutil
import subprocess
from pathlib import Path

import pytest

from omphalos.ignore import (
    NotAGitRepoError,
    collect_files,
    collect_git_files,
    ensure_ignore_file,
    load_ignore_spec,
)

PY_JS = {".py", ".js"}


def make_tree(tmp_path: Path):
    for rel in ["src/a.py", "src/notes.txt", "build/out.py", "node_modules/deep/x.js"]:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x = 1\n", encoding="utf-8")


def collected_rel(tmp_path: Path, spec) -> set[str]:
    files = collect_files(tmp_path, spec, PY_JS)
    return {f.relative_to(tmp_path).as_posix() for f in files}


def test_ensure_ignore_file_creates_when_missing(tmp_path: Path):
    created = ensure_ignore_file(tmp_path)
    assert created is not None
    assert created.name == ".omphalos_ignore"
    assert created.exists()


def test_ensure_ignore_file_respects_existing(tmp_path: Path):
    (tmp_path / ".omphalos_ignore").write_text("node_modules/\n", encoding="utf-8")
    assert ensure_ignore_file(tmp_path) is None


def test_collect_files_skips_ignored_dirs_and_extensions(tmp_path: Path):
    make_tree(tmp_path)
    spec = load_ignore_spec(tmp_path)
    # build/ และ node_modules/ ถูก ignore จาก defaults, .txt ไม่อยู่ในนามสกุลที่รองรับ
    assert collected_rel(tmp_path, spec) == {"src/a.py"}


def test_negation_can_reinclude_directory(tmp_path: Path):
    make_tree(tmp_path)
    (tmp_path / ".omphalos_ignore").write_text("!build/\n", encoding="utf-8")
    spec = load_ignore_spec(tmp_path)
    assert "build/out.py" in collected_rel(tmp_path, spec)


def test_negation_inside_excluded_dir_does_not_apply(tmp_path: Path):
    # ตาม semantics ของ git: re-include ไฟล์ในโฟลเดอร์ที่ถูก ignore ทั้งโฟลเดอร์ไม่ได้
    make_tree(tmp_path)
    (tmp_path / ".omphalos_ignore").write_text("!build/keep.py\n", encoding="utf-8")
    spec = load_ignore_spec(tmp_path)
    assert "build/out.py" not in collected_rel(tmp_path, spec)


def test_omphalos_ignore_overrides_gitignore(tmp_path: Path):
    make_tree(tmp_path)
    (tmp_path / ".gitignore").write_text("src/\n", encoding="utf-8")
    (tmp_path / ".omphalos_ignore").write_text("!src/\n", encoding="utf-8")
    spec = load_ignore_spec(tmp_path)
    assert collected_rel(tmp_path, spec) == {"src/a.py"}


def test_collect_files_is_sorted(tmp_path: Path):
    for rel in ["z.py", "a/b.py", "a.py"]:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x = 1\n", encoding="utf-8")
    spec = load_ignore_spec(tmp_path)
    files = collect_files(tmp_path, spec, {".py"})
    assert files == sorted(files)


GIT_AVAILABLE = shutil.which("git") is not None


def init_git_repo(tmp_path: Path, tracked: list[str], untracked: list[str]):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    for rel in tracked:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", rel], cwd=tmp_path, check=True)
    for rel in untracked:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x = 1\n", encoding="utf-8")


@pytest.mark.skipif(not GIT_AVAILABLE, reason="git not available")
def test_collect_git_files_only_tracked(tmp_path: Path):
    init_git_repo(tmp_path, tracked=["src/a.py"], untracked=["src/secret.py", "notes.txt"])
    spec = load_ignore_spec(tmp_path)
    files = collect_git_files(tmp_path, spec, {".py"})
    rels = {f.relative_to(tmp_path).as_posix() for f in files}
    assert rels == {"src/a.py"}


@pytest.mark.skipif(not GIT_AVAILABLE, reason="git not available")
def test_collect_git_files_outside_repo_raises(tmp_path: Path):
    spec = load_ignore_spec(tmp_path)
    with pytest.raises(NotAGitRepoError):
        collect_git_files(tmp_path, spec, {".py"})
