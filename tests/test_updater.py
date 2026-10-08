# tests/test_updater.py
import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from omphalos.updater import (
    check_for_update,
    fetch_latest_pypi_version,
    format_update_notice,
    is_newer_version,
    notify_if_update_available,
    parse_version,
    read_cached_version,
    write_cached_version,
)


def test_parse_version():
    assert parse_version("1.1.2") == (1, 1, 2)
    assert parse_version("v1.2.0") == (1, 2, 0)
    assert parse_version("2.0.0") == (2, 0, 0)
    assert parse_version("") == (0,)


def test_is_newer_version():
    assert is_newer_version("1.2.0", "1.1.2") is True
    assert is_newer_version("1.1.3", "1.1.2") is True
    assert is_newer_version("2.0.0", "1.9.9") is True
    assert is_newer_version("1.1.2", "1.1.2") is False
    assert is_newer_version("1.0.5", "1.1.2") is False


def test_cache_read_write(tmp_path: Path):
    cache_file = tmp_path / "update.json"
    ts, ver = read_cached_version(cache_file)
    assert ts == 0.0
    assert ver is None

    # Write corrupt data
    cache_file.write_text("invalid json", encoding="utf-8")
    ts, ver = read_cached_version(cache_file)
    assert ts == 0.0
    assert ver is None

    # Write valid data
    now = 1700000000.0
    write_cached_version(cache_file, now, "1.2.0")
    ts, ver = read_cached_version(cache_file)
    assert ts == now
    assert ver == "1.2.0"


def test_check_for_update_cached_within_ttl(tmp_path: Path, monkeypatch):
    cache_file = tmp_path / "update.json"
    now = time.time()
    # Cache created 1 hour ago with version 1.2.0
    write_cached_version(cache_file, now - 3600, "1.2.0")

    # Network should NOT be called
    monkeypatch.setattr("omphalos.updater.fetch_latest_pypi_version", lambda **kw: pytest.fail("Should not call net"))

    latest = check_for_update("1.1.2", cache_path=cache_file)
    assert latest == "1.2.0"

    # If current is already 1.2.0, returns None
    latest_same = check_for_update("1.2.0", cache_path=cache_file)
    assert latest_same is None


def test_check_for_update_fetches_when_expired(tmp_path: Path, monkeypatch):
    cache_file = tmp_path / "update.json"
    now = time.time()
    # Expired cache (2 days ago)
    write_cached_version(cache_file, now - 180000, "1.1.0")

    monkeypatch.setattr("omphalos.updater.fetch_latest_pypi_version", lambda **kw: "1.3.0")

    latest = check_for_update("1.1.2", cache_path=cache_file)
    assert latest == "1.3.0"

    # Cache should be updated with new timestamp and version
    ts, cached_ver = read_cached_version(cache_file)
    assert cached_ver == "1.3.0"
    assert ts >= now - 5


def test_check_for_update_handles_network_failure(tmp_path: Path, monkeypatch):
    cache_file = tmp_path / "update.json"
    # Network throws exception
    monkeypatch.setattr("omphalos.updater.fetch_latest_pypi_version", lambda **kw: None)

    latest = check_for_update("1.1.2", cache_path=cache_file)
    assert latest is None


def test_fetch_latest_pypi_version_success(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"info": {"version": "9.9.9"}}).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout: mock_resp)
    assert fetch_latest_pypi_version() == "9.9.9"


def test_fetch_latest_pypi_version_network_error(monkeypatch):
    def raise_err(req, timeout):
        raise OSError("network down")

    monkeypatch.setattr("urllib.request.urlopen", raise_err)
    assert fetch_latest_pypi_version() is None


def test_format_update_notice():
    notice = format_update_notice("1.1.2", "1.2.0")
    assert "1.1.2 → 1.2.0" in notice
    assert "uv tool upgrade omphalos" in notice
    assert "npm install -g omphalos" in notice
    assert "╭" in notice and "╯" in notice


def test_notify_suppressed_in_ci(monkeypatch):
    monkeypatch.setenv("CI", "true")
    echoed = []
    monkeypatch.setattr("typer.echo", lambda msg: echoed.append(msg))
    notify_if_update_available("1.1.2")
    assert len(echoed) == 0


def test_notify_suppressed_in_json_and_check(monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    echoed = []
    monkeypatch.setattr("typer.echo", lambda msg: echoed.append(msg))
    notify_if_update_available("1.1.2", is_json=True)
    notify_if_update_available("1.1.2", is_check=True)
    assert len(echoed) == 0


def test_notify_prints_when_update_available(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("OMPH_NO_UPDATE_NOTIFIER", raising=False)
    cache_file = tmp_path / "update.json"
    write_cached_version(cache_file, time.time(), "2.0.0")

    echoed = []
    monkeypatch.setattr("typer.echo", lambda msg: echoed.append(msg))

    notify_if_update_available("1.1.2", cache_path=cache_file)
    assert len(echoed) == 1
    assert "1.1.2 → 2.0.0" in echoed[0]
