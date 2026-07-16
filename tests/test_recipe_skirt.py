"""Unit tests for the demo A-line skirt recipe."""

import pytest

from pattern_forge.recipes import AlineSkirt
from pattern_forge.validators import validate_pattern_xml


def test_default_draft_is_xsd_valid():
    doc = AlineSkirt().draft({"waist_circ": 90})
    assert validate_pattern_xml(doc.to_string()) == []


def test_geometry_is_parametric():
    xml = AlineSkirt().draft({"waist_circ": 90}).to_string()
    # geometry must reference the variables, not hardcoded numbers
    assert 'length="#WaistCirc/4"' in xml
    assert 'length="#WaistCirc/4 + #Flare"' in xml
    assert 'name="#SkirtLength"' in xml


def test_piece_has_label_and_grainline():
    """README promises every piece prints with a label and grainline —
    including this demo recipe."""
    xml = AlineSkirt().draft({"waist_circ": 90}).to_string()
    assert xml.count('visible="true"') >= 2  # 1 label + 1 grainline


def test_options_change_variables():
    xml = AlineSkirt().draft({"waist_circ": 90}, {"skirt_length": 75}).to_string()
    assert 'formula="75"' in xml


def test_missing_measurement_rejected():
    with pytest.raises(ValueError, match="missing measurement: waist_circ"):
        AlineSkirt().draft({})


def test_implausible_measurement_rejected():
    with pytest.raises(ValueError, match="outside the plausible range"):
        AlineSkirt().draft({"waist_circ": 20})


def test_unsafe_option_rejected():
    with pytest.raises(ValueError, match="outside the safe range"):
        AlineSkirt().draft({"waist_circ": 90}, {"flare": 100})


def test_unknown_option_rejected():
    with pytest.raises(ValueError, match="unknown option"):
        AlineSkirt().draft({"waist_circ": 90}, {"pockets": 2})
