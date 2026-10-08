# omphalos/updater.py
from __future__ import annotations

import json
import os
import re
import tempfile
import time
import urllib.request
from pathlib import Path

PYPI_URL = "https://pypi.org/pypi/omphalos/json"
DEFAULT_TTL_SECONDS = 86400.0  # 24 hours


def parse_version(v: str) -> tuple[int, ...]:
    """Parse semver string into comparable tuple of ints."""
    clean = v.strip().lstrip("v")
    nums = re.findall(r"\d+", clean)
    return tuple(int(n) for n in nums) if nums else (0,)


def is_newer_version(latest: str, current: str) -> bool:
    """Return True if latest is strictly newer than current version."""
    try:
        from packaging.version import parse as pkg_parse
        return pkg_parse(latest) > pkg_parse(current)
    except Exception:
        return parse_version(latest) > parse_version(current)


def get_update_cache_path() -> Path:
    """Return user cache path for update checks."""
    base = Path.home() / ".omphalos"
    return base / "update_check.json"


def read_cached_version(cache_path: Path) -> tuple[float, str | None]:
    """Read last check timestamp and cached latest version."""
    if not cache_path.is_file():
        return (0.0, None)
    try:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            last_check = float(raw.get("last_check", 0.0))
            latest = raw.get("latest_version")
            return (last_check, str(latest) if latest else None)
    except Exception:
        pass
    return (0.0, None)


def write_cached_version(cache_path: Path, timestamp: float, latest_version: str | None) -> None:
    """Persist last check timestamp and latest version to cache file atomically."""
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "last_check": timestamp,
            "latest_version": latest_version,
        }
        encoded = json.dumps(data, indent=2)
        dir_name = str(cache_path.parent)
        fd, tmp_file = tempfile.mkstemp(dir=dir_name, prefix=".upd_tmp_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(encoded)
            os.replace(tmp_file, str(cache_path))
        except BaseException:
            if os.path.exists(tmp_file):
                os.unlink(tmp_file)
            raise
    except Exception:
        pass


def fetch_latest_pypi_version(timeout: float = 1.0) -> str | None:
    """Query PyPI JSON API for latest version string."""
    try:
        req = urllib.request.Request(
            PYPI_URL,
            headers={"User-Agent": "omphalos-updater"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            info = data.get("info", {})
            ver = info.get("version")
            return str(ver) if ver else None
    except Exception:
        return None


def check_for_update(
    current_version: str,
    cache_path: Path | None = None,
    timeout: float = 1.0,
    ttl: float = DEFAULT_TTL_SECONDS,
) -> str | None:
    """Check if a newer version is available.

    Uses a cached check if performed within TTL to avoid network overhead.
    Returns the latest version string if newer than current_version, else None.
    """
    if not current_version or current_version == "unknown":
        return None

    path = cache_path if cache_path is not None else get_update_cache_path()
    now = time.time()
    last_check, cached_latest = read_cached_version(path)

    if now - last_check < ttl:
        if cached_latest and is_newer_version(cached_latest, current_version):
            return cached_latest
        return None

    # TTL expired: fetch from PyPI
    latest = fetch_latest_pypi_version(timeout=timeout)
    # Update cache (even on failure, record timestamp to avoid hammer on network error)
    saved_version = latest if latest else cached_latest
    write_cached_version(path, now, saved_version)

    if latest and is_newer_version(latest, current_version):
        return latest
    return None


def format_update_notice(current: str, latest: str, color: bool = True) -> str:
    """Generate a clean, styled CLI notice box for available updates."""
    line1 = f"Update available: {current} → {latest}"
    line2 = "To upgrade, run:"
    line3 = "  uv tool upgrade omphalos"
    line4 = "  or: npm install -g omphalos"

    content_lines = [line1, line2, line3, line4]
    max_len = max(len(line) for line in content_lines)
    box_width = max_len + 4

    top_border = "╭" + "─" * box_width + "╮"
    bot_border = "╰" + "─" * box_width + "╯"

    if color:
        import typer
        top = typer.style(top_border, fg=typer.colors.CYAN)
        bot = typer.style(bot_border, fg=typer.colors.CYAN)
        b_l = typer.style("│  ", fg=typer.colors.CYAN)
        b_r = typer.style("  │", fg=typer.colors.CYAN)

        def pad_styled(raw: str, styled: str) -> str:
            return b_l + styled + (" " * (max_len - len(raw))) + b_r

        l1 = pad_styled(
            line1,
            typer.style("Update available: ", bold=True)
            + typer.style(f"{current} → {latest}", fg=typer.colors.GREEN, bold=True),
        )
        l2 = pad_styled(line2, typer.style(line2, fg=typer.colors.WHITE))
        l3 = pad_styled(line3, "  " + typer.style("uv tool upgrade omphalos", fg=typer.colors.CYAN, bold=True))
        l4 = pad_styled(line4, "  " + typer.style("or: npm install -g omphalos", fg=typer.colors.BRIGHT_BLACK))
        body = "\n".join([l1, l2, l3, l4])
    else:
        top = top_border
        bot = bot_border
        body = "\n".join("│  " + line + " " * (box_width - len(line) - 2) + "│" for line in content_lines)

    return f"\n{top}\n{body}\n{bot}\n"


def notify_if_update_available(
    current_version: str,
    is_json: bool = False,
    is_check: bool = False,
    cache_path: Path | None = None,
) -> None:
    """Print update notification if a newer version is available and not suppressed."""
    if is_json or is_check:
        return
    if os.environ.get("OMPH_NO_UPDATE_NOTIFIER") or os.environ.get("CI"):
        return

    try:
        latest = check_for_update(current_version, cache_path=cache_path)
        if latest:
            import typer
            typer.echo(format_update_notice(current_version, latest))
    except Exception:
        pass
