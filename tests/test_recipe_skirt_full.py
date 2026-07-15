"""Tests for the full A-line skirt recipe (front + back + waistband)."""

import pytest
from conftest import needs_seamly2d

from pattern_forge.recipes import Skirt
from pattern_forge.seamly_cli import validate_pattern
from pattern_forge.validators import validate_pattern_xml

BODIES = [
    ("woman_s", {"waist_circ": 66, "hip_circ": 92}),
    ("woman_m", {"waist_circ": 76, "hip_circ": 100}),
    ("woman_xl", {"waist_circ": 95, "hip_circ": 118}),
]


@pytest.mark.parametrize("body", BODIES, ids=[b[0] for b in BODIES])
def test_drafts_and_is_xsd_valid(body):
    doc = Skirt().draft(body[1])
    assert validate_pattern_xml(doc.to_string()) == []


def test_has_three_pieces_with_labels_and_grainlines():
    xml = Skirt().draft(BODIES[1][1]).to_string()
    for piece in ("SkirtFront", "SkirtBack", "SkirtWaistband"):
        assert f'name="{piece}"' in xml
    assert xml.count('visible="true"') >= 6  # 3 labels + 3 grainlines
    assert 'text="cut 1 on fold"' in xml


def test_waist_larger_than_hip_rejected():
    with pytest.raises(ValueError, match="waist is too large relative to hip"):
        Skirt().draft({"waist_circ": 110, "hip_circ": 95})


def test_hip_height_vs_length_rejected():
    with pytest.raises(ValueError, match="skirt_length must be greater"):
        Skirt().draft(BODIES[1][1], {"skirt_length": 26, "hip_height": 26})


@needs_seamly2d
@pytest.mark.parametrize("body", BODIES, ids=[b[0] for b in BODIES])
def test_gate_computes_in_seamly2d(tmp_path, body):
    doc = Skirt().draft(body[1])
    path = doc.save(tmp_path / f"skirt_{body[0]}.sm2d")
    result = validate_pattern(path)
    assert result.ok, f"{body[0]}: exit {result.exit_code}\n{result.stderr}"
