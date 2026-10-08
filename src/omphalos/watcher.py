# omphalos/watcher.py
from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from omphalos.ignore import NotAGitRepoError, collect_files, collect_git_files, load_ignore_spec
from omphalos.parser import SUPPORTED_EXTENSIONS

FileSnapshot = dict[Path, tuple[int, int]]


def snapshot_workspace(root: Path, git_only: bool = False) -> tuple[FileSnapshot, list[Path]]:
    """Take a timestamp/size snapshot of all tracked codebase and ignore files."""
    spec = load_ignore_spec(root)
    if git_only:
        target_files = collect_git_files(root, spec, SUPPORTED_EXTENSIONS)
    else:
        target_files = collect_files(root, spec, SUPPORTED_EXTENSIONS)

    snapshot: FileSnapshot = {}
    for p in target_files:
        try:
            st = p.stat()
            snapshot[p] = (st.st_mtime_ns, st.st_size)
        except OSError:
            pass

    # Include ignore files so editing .omphignore or .gitignore triggers a re-index
    for ign_name in (".omphignore", ".gitignore"):
        ign_path = root / ign_name
        if ign_path.exists():
            try:
                st = ign_path.stat()
                snapshot[ign_path] = (st.st_mtime_ns, st.st_size)
            except OSError:
                pass

    return snapshot, target_files


def detect_changes(prev: FileSnapshot, curr: FileSnapshot) -> list[Path]:
    """Return paths of added, modified, or deleted files between two snapshots."""
    changed: list[Path] = []
    # Added or modified files
    for path, stat in curr.items():
        if path not in prev or prev[path] != stat:
            changed.append(path)
    # Deleted files
    for path in prev:
        if path not in curr:
            changed.append(path)
    return changed


def watch_loop(
    root: Path,
    on_change: Callable[[list[Path]], None],
    git_only: bool = False,
    poll_interval: float = 0.5,
    debounce_delay: float = 0.25,
    max_cycles: int | None = None,
    stop_check: Callable[[], bool] | None = None,
    initial_snapshot: FileSnapshot | None = None,
) -> None:
    """Continuously poll workspace for changes and trigger on_change callback.

    Args:
        root: Workspace directory to watch.
        on_change: Callback invoked with the list of changed file paths.
        git_only: Only watch files tracked by git.
        poll_interval: Seconds between snapshot checks.
        debounce_delay: Seconds to wait after changes detected to settle bursts.
        max_cycles: Optional maximum poll iterations (for testing).
        stop_check: Optional callable returning True to stop the loop.
        initial_snapshot: Optional pre-existing snapshot of the workspace.
    """
    if initial_snapshot is not None:
        prev_snapshot = dict(initial_snapshot)
    else:
        try:
            prev_snapshot, _ = snapshot_workspace(root, git_only=git_only)
        except NotAGitRepoError:
            return
    cycles = 0

    while True:
        if max_cycles is not None and cycles >= max_cycles:
            break
        if stop_check and stop_check():
            break

        time.sleep(poll_interval)
        cycles += 1

        try:
            curr_snapshot, _ = snapshot_workspace(root, git_only=git_only)
        except NotAGitRepoError:
            break

        changes = detect_changes(prev_snapshot, curr_snapshot)
        if changes:
            if debounce_delay > 0:
                time.sleep(debounce_delay)
                try:
                    curr_snapshot, _ = snapshot_workspace(root, git_only=git_only)
                except NotAGitRepoError:
                    break
                changes = detect_changes(prev_snapshot, curr_snapshot)

            prev_snapshot = curr_snapshot
            if changes:
                on_change(changes)
