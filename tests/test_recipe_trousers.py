"""Trousers recipe tests: unit-level + the Phase-1 size-matrix gate."""

import pytest
from conftest import needs_seamly2d

from pattern_forge.recipes import Trousers
from pattern_forge.seamly_cli import ExportFormat, export_pattern, validate_pattern
from pattern_forge.validators import validate_pattern_xml

# realistic body matrix: (label, waist, hip, waist_height, crotch_height, knee_height)
BODIES = [
    ("small_woman", 62, 88, 100, 74, 45),
    ("average_woman", 72, 98, 104, 77, 47),
    ("curvy_woman", 90, 112, 106, 78, 48),
    ("average_man", 84, 100, 107, 83, 50),
    ("big_man", 110, 118, 110, 82, 50),
    ("slim_tall_man", 76, 94, 115, 88, 54),
    ("short_person", 80, 102, 95, 68, 42),
    ("plus_size", 120, 130, 105, 76, 47),
]


def body_measurements(body) -> dict[str, float]:
    _, waist, hip, wh, ch, kh = body
    return {
        "waist_circ": waist,
        "hip_circ": hip,
        "height_waist_side": wh,
        "leg_crotch_to_floor": ch,
        "height_knee": kh,
    }


@pytest.mark.parametrize("body", BODIES, ids=[b[0] for b in BODIES])
def test_matrix_drafts_and_is_xsd_valid(body):
    doc = Trousers().draft(body_measurements(body))
    assert validate_pattern_xml(doc.to_string()) == []


def test_has_three_pieces():
    xml = Trousers().draft(body_measurements(BODIES[3])).to_string()
    for piece in ("TrousersFront", "TrousersBack", "Waistband"):
        assert f'name="{piece}"' in xml


def test_inseam_match_by_construction():
    """The back crotch point must reference the front inseam length variable."""
    xml = Trousers().draft(body_measurements(BODIES[3])).to_string()
    assert 'length="Line_KneeFIn_CrotchPointF"' in xml


def test_impossible_frame_rejected():
    bad = body_measurements(BODIES[3]) | {"height_knee": 60, "leg_crotch_to_floor": 58}
    with pytest.raises(ValueError, match="vertical frame"):
        Trousers().draft(bad)


def test_check_inputs_never_raises_on_partial_options():
    """REGRESSION (review finding): public check_inputs must return errors,
    not raise KeyError, when called with an incomplete options dict."""
    assert Trousers().check_inputs(body_measurements(BODIES[3]), {}) == []
    assert Trousers().check_inputs(body_measurements(BODIES[3]), None) == []


def test_front_side_seam_inversion_rejected():
    """REGRESSION (review finding): the front panel is narrower at the hip than
    the back, so it inverts first — the check must guard it, not only the back."""
    # waist 84 / hip 100: front margin = 25 - 9.9 = 15.1; knee_circ 66 makes the
    # front knee half 16.0 (inverts) while the back margin 20.25 > 17.0 (passes)
    errors = Trousers().check_inputs(
        body_measurements(BODIES[3]), {"knee_circ": 66})
    assert any("front side seam" in e for e in errors), errors


def test_impossible_frame_returns_errors_without_crashing():
    """REGRESSION (review finding): a degenerate frame used to keep computing
    and could divide by zero; now the frame error returns immediately."""
    # these values make the knee line coincide with the hip line, which drove
    # direction_len to exactly 0 before the early return
    degenerate = {
        "waist_circ": 80, "hip_circ": 140, "height_waist_side": 110,
        "leg_crotch_to_floor": 55, "height_knee": 65,
    }
    errors = Trousers().check_inputs(degenerate, {"hip_ease": 8, "knee_circ": 37})
    assert errors and any("vertical frame" in e for e in errors)


def test_output_matches_committed_golden():
    """Locks the emitted .sm2d format: any change to writer or recipe output
    shows up as a diff against the committed golden (regenerate deliberately
    with Trousers().draft(...).to_string() if the change is intended)."""
    from pathlib import Path

    golden = Path(__file__).parent / "data" / "generated_trousers_avg_man.sm2d"
    xml = Trousers().draft(body_measurements(BODIES[3])).to_string()
    assert xml == golden.read_text(encoding="utf-8")


def test_pieces_are_auto_spread():
    """Pieces get distinct auto-placement offsets (details-mode overlap guard)."""
    xml = Trousers().draft(body_measurements(BODIES[3])).to_string()
    import re

    offsets = re.findall(r'<piece[^>]* mx="([^"]+)"', xml)
    assert len(offsets) == 3
    assert len(set(offsets)) == 3, f"pieces share a position: {offsets}"


@needs_seamly2d
@pytest.mark.parametrize("body", BODIES, ids=[b[0] for b in BODIES])
def test_gate_matrix_computes_in_seamly2d(tmp_path, body):
    """PHASE 1 GATE: every body in the matrix computes in the real Seamly2D."""
    doc = Trousers().draft(body_measurements(body))
    path = doc.save(tmp_path / f"trousers_{body[0]}.sm2d")
    result = validate_pattern(path)
    assert result.ok, f"{body[0]}: exit {result.exit_code}\n{result.stderr}\n{result.stdout}"


@needs_seamly2d
def test_gate_export_layout(tmp_path):
    """PHASE 1 GATE: the generated trousers export a real layout (SVG)."""
    doc = Trousers().draft(body_measurements(BODIES[3]))
    path = doc.save(tmp_path / "trousers.sm2d")
    result = export_pattern(path, tmp_path, "layout", ExportFormat.SVG)
    assert result.ok, f"exit {result.exit_code}\n{result.stderr}"
    assert result.produced
