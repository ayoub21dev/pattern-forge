"""Unit tests for the .smis measurements writer."""

import pytest

from pattern_forge.smis import MeasurementsFile
from pattern_forge.validators import validate_smis_xml


def build_sample() -> MeasurementsFile:
    m = MeasurementsFile(unit="cm")
    m.set_many(
        {
            "waist_circ": 84,
            "hip_circ": 100,
            "height_knee": 50,
            "leg_crotch_to_floor": 83,
        }
    )
    return m


def test_smis_is_xsd_valid():
    errors = validate_smis_xml(build_sample().to_string())
    assert errors == []


def test_values_roundtrip():
    m = build_sample()
    assert m.get("waist_circ") == 84
    assert set(m.names) == {"waist_circ", "hip_circ", "height_knee", "leg_crotch_to_floor"}


def test_structure_basics():
    xml = build_sample().to_string()
    assert "<version>0.3.4</version>" in xml
    assert '<m name="waist_circ" value="84" />' in xml or '<m name="waist_circ" value="84"/>' in xml


def test_empty_name_rejected():
    with pytest.raises(ValueError):
        MeasurementsFile().set("", 10)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf"), -5, 0])
def test_non_positive_or_non_finite_values_rejected(bad):
    """REGRESSION (review finding): garbage values must fail at set(), not
    surface later inside a Seamly2D formula."""
    with pytest.raises(ValueError):
        MeasurementsFile().set("waist_circ", bad)


@pytest.mark.parametrize("bad", ["waist circ", "1hip", "hip-circ", "wa$ist"])
def test_invalid_names_rejected(bad):
    with pytest.raises(ValueError):
        MeasurementsFile().set(bad, 84)


def test_custom_at_name_accepted():
    m = MeasurementsFile()
    m.set("@custom_x", 5)
    assert m.get("@custom_x") == 5
