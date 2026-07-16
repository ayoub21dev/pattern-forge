"""Tests for the binary lookup in config.py."""

from pathlib import Path

import pytest

from pattern_forge import config


@pytest.fixture(autouse=True)
def clean_cache():
    """Each test starts with an empty positive-only cache."""
    config._found.clear()
    yield
    config._found.clear()


def test_stale_env_var_returns_none_with_warning(monkeypatch):
    """REGRESSION (review finding): a set-but-wrong env var must not raise —
    callers None-guard, and pytest collection itself calls find_seamly2d()."""
    monkeypatch.setenv("PATTERN_FORGE_SEAMLY2D", r"C:\does\not\exist\seamly2d.exe")
    with pytest.warns(UserWarning, match="does not exist"):
        assert config.find_seamly2d() is None


def test_env_var_pointing_at_real_file_wins(monkeypatch, tmp_path):
    fake = tmp_path / "seamly2d.exe"
    fake.write_bytes(b"")
    monkeypatch.setenv("PATTERN_FORGE_SEAMLY2D", str(fake))
    assert config.find_seamly2d() == fake


def test_miss_is_not_cached_forever(monkeypatch, tmp_path):
    """REGRESSION (review finding): a not-found result must be re-checked, so a
    binary installed mid-session is detected without restarting the server."""
    calls = {"n": 0}
    fake = tmp_path / "seamly2d.exe"

    def locate(exe_name, env_var):
        calls["n"] += 1
        return fake if fake.is_file() else None

    monkeypatch.setattr(config, "_locate", locate)
    assert config._find_binary("seamly2d.exe", "PATTERN_FORGE_SEAMLY2D") is None
    fake.write_bytes(b"")  # "install" the binary mid-session
    assert config._find_binary("seamly2d.exe", "PATTERN_FORGE_SEAMLY2D") == fake
    # and hits ARE cached: a third call must not re-locate
    assert config._find_binary("seamly2d.exe", "PATTERN_FORGE_SEAMLY2D") == fake
    assert calls["n"] == 2
