"""Shared test fixtures and markers."""

import os

import pytest

from pattern_forge.config import find_seamly2d, find_seamlyme

#: set PATTERN_FORGE_REQUIRE_SEAMLY=1 to make the binary-gated tests RUN (and
#: fail loudly via SeamlyNotFoundError) instead of silently skipping — use in
#: CI where a green suite must mean the real Seamly2D validation actually ran
_REQUIRE = os.environ.get("PATTERN_FORGE_REQUIRE_SEAMLY") == "1"

#: skip markers for tests that need the real binaries (defined once, imported by tests)
needs_seamly2d = pytest.mark.skipif(
    not _REQUIRE and find_seamly2d() is None,
    reason="seamly2d.exe not found (set PATTERN_FORGE_REQUIRE_SEAMLY=1 to fail instead of skip)")
needs_seamlyme = pytest.mark.skipif(
    not _REQUIRE and find_seamlyme() is None,
    reason="seamlyme.exe not found (set PATTERN_FORGE_REQUIRE_SEAMLY=1 to fail instead of skip)")


def pytest_report_header(config):
    """Make silently-skipped real-binary validation visible in every run."""
    s2d, sme = find_seamly2d(), find_seamlyme()
    return (f"seamly2d: {s2d or 'NOT FOUND - real-binary gate tests will SKIP'} | "
            f"seamlyme: {sme or 'NOT FOUND'}")

#: one canonical "average man" measurement set used across suites
AVG_MAN = {
    "waist_circ": 84,
    "hip_circ": 100,
    "height_waist_side": 107,
    "leg_crotch_to_floor": 83,
    "height_knee": 50,
}
