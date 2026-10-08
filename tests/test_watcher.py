# tests/test_watcher.py
import shutil
import subprocess
import threading
import time
from pathlib import Path

import pytest

from omphalos.watcher import detect_changes, snapshot_workspace, watch_loop

GIT_AVAILABLE = shutil.which("git") is not None


def test_snapshot_workspace_and_detect_changes(tmp_path: Path):
    py_file = tmp_path / "hello.py"
    py_file.write_text("def hello(): pass\n", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("text\n", encoding="utf-8")

    snap1, targets = snapshot_workspace(tmp_path)
    assert py_file in snap1
    assert py_file in targets
    assert (tmp_path / "ignored.txt") not in snap1

    # Modify file
    py_file.write_text("def hello(): return 42\n", encoding="utf-8")
    snap2, _ = snapshot_workspace(tmp_path)
    changes = detect_changes(snap1, snap2)
    assert py_file in changes

    # Add new file
    ts_file = tmp_path / "app.ts"
    ts_file.write_text("export const x = 1;\n", encoding="utf-8")
    snap3, _ = snapshot_workspace(tmp_path)
    changes_add = detect_changes(snap2, snap3)
    assert ts_file in changes_add

    # Delete file
    ts_file.unlink()
    snap4, _ = snapshot_workspace(tmp_path)
    changes_del = detect_changes(snap3, snap4)
    assert ts_file in changes_del


def test_snapshot_workspace_tracks_ignore_files(tmp_path: Path):
    omphignore = tmp_path / ".omphignore"
    omphignore.write_text("*.tmp\n", encoding="utf-8")
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(".env\n", encoding="utf-8")

    snap1, _ = snapshot_workspace(tmp_path)
    assert omphignore in snap1
    assert gitignore in snap1

    # Modifying .omphignore is detected
    time.sleep(0.01)
    omphignore.write_text("*.tmp\n*.log\n", encoding="utf-8")
    snap2, _ = snapshot_workspace(tmp_path)
    changes = detect_changes(snap1, snap2)
    assert omphignore in changes


@pytest.mark.skipif(not GIT_AVAILABLE, reason="git not available")
def test_snapshot_workspace_git_only(tmp_path: Path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    tracked_py = tmp_path / "tracked.py"
    tracked_py.write_text("def t(): pass\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.py"], cwd=tmp_path, check=True)

    untracked_py = tmp_path / "untracked.py"
    untracked_py.write_text("def u(): pass\n", encoding="utf-8")

    snap, targets = snapshot_workspace(tmp_path, git_only=True)
    assert tracked_py in snap
    assert tracked_py in targets
    assert untracked_py not in snap
    assert untracked_py not in targets


def test_watch_loop_invokes_on_change_with_initial_snapshot(tmp_path: Path):
    py_file = tmp_path / "worker.py"
    py_file.write_text("def work(): pass\n", encoding="utf-8")
    snap1, _ = snapshot_workspace(tmp_path)

    # Mutate file after snapshot
    py_file.write_text("def work(): return True\n", encoding="utf-8")

    invoked_changes = []

    def on_change(changes: list[Path]):
        invoked_changes.append(list(changes))

    watch_loop(
        root=tmp_path,
        on_change=on_change,
        poll_interval=0.01,
        debounce_delay=0.01,
        max_cycles=1,
        initial_snapshot=snap1,
    )

    assert len(invoked_changes) == 1
    assert py_file in invoked_changes[0]


def test_watch_loop_with_background_thread_and_stop_check(tmp_path: Path):
    py_file = tmp_path / "thread_test.py"
    py_file.write_text("def a(): pass\n", encoding="utf-8")

    invoked_changes = []
    stop_flag = False

    def on_change(changes: list[Path]):
        nonlocal stop_flag
        invoked_changes.append(list(changes))
        stop_flag = True

    def writer():
        time.sleep(0.04)
        py_file.write_text("def a(): return 123\n", encoding="utf-8")

    t = threading.Thread(target=writer)
    t.start()

    watch_loop(
        root=tmp_path,
        on_change=on_change,
        poll_interval=0.02,
        debounce_delay=0.01,
        max_cycles=20,
        stop_check=lambda: stop_flag,
    )
    t.join()

    assert len(invoked_changes) >= 1
    assert py_file in invoked_changes[0]


def test_watch_loop_debounce_aggregates_rapid_changes(tmp_path: Path):
    file1 = tmp_path / "mod1.py"
    file2 = tmp_path / "mod2.py"
    file1.write_text("def m1(): pass\n", encoding="utf-8")
    file2.write_text("def m2(): pass\n", encoding="utf-8")

    snap1, _ = snapshot_workspace(tmp_path)

    invoked = []

    def on_change(changes: list[Path]):
        invoked.append(list(changes))

    # Mutate both files
    file1.write_text("def m1(): return 1\n", encoding="utf-8")
    file2.write_text("def m2(): return 2\n", encoding="utf-8")

    watch_loop(
        root=tmp_path,
        on_change=on_change,
        poll_interval=0.01,
        debounce_delay=0.05,
        max_cycles=1,
        initial_snapshot=snap1,
    )

    # Both changes aggregated into one callback invocation
    assert len(invoked) == 1
    assert file1 in invoked[0]
    assert file2 in invoked[0]


def test_watch_loop_exits_on_not_a_git_repo(tmp_path: Path):
    called = []
    watch_loop(
        root=tmp_path,
        on_change=lambda ch: called.append(ch),
        git_only=True,
        poll_interval=0.01,
        debounce_delay=0.01,
        max_cycles=5,
    )
    assert len(called) == 0
