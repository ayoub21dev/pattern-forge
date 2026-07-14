"""Shared test fixtures and markers."""

import pytest

from pattern_forge.config import find_seamly2d, find_seamlyme

#: skip markers for tests that need the real binaries (defined once, imported by tests)
needs_seamly2d = pytest.mark.skipif(find_seamly2d() is None, reason="seamly2d.exe not found")
needs_seamlyme = pytest.mark.skipif(find_seamlyme() is None, reason="seamlyme.exe not found")

#: one canonical "average man" measurement set used across suites
AVG_MAN = {
    "waist_circ": 84,
    "hip_circ": 100,
    "height_waist_side": 107,
    "leg_crotch_to_floor": 83,
    "height_knee": 50,
}
