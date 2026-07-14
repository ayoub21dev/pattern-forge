"""Unit tests for the .sm2d document writer."""

import pytest

from pattern_forge.sm2d import Document
from pattern_forge.validators import validate_pattern_xml


def build_sample_doc() -> Document:
    """A small document exercising every element type the writer supports."""
    doc = Document(unit="cm", description="writer test", notes="notes")
    doc.add_increment("#Width", 20, "test width")
    block = doc.add_draft_block("Test")
    a = block.add_base_point("A", x=1, y=1)
    b = block.add_end_line_point("B", base=a, angle=0, length="#Width")
    c = block.add_end_line_point("C", base=a, angle=270, length=30, line_type="solidLine")
    d = block.add_along_line_point("D", first=a, second=b, length="#Width/2")
    e = block.add_normal_point("E", first=a, second=b, length=5)
    block.add_line(b, c)
    block.add_simple_spline(c, b, angle1=0, angle2=183, length1=5, length2=5)
    assert [p.id for p in (a, b, c, d, e)] == [1, 2, 3, 4, 5]
    return doc


def test_ids_are_sequential_and_unique():
    doc = build_sample_doc()
    xml = doc.to_string()
    import re

    ids = [int(m) for m in re.findall(r'id="(\d+)"', xml)]
    assert ids == sorted(ids)
    assert len(ids) == len(set(ids))


def test_document_is_xsd_valid():
    doc = build_sample_doc()
    errors = validate_pattern_xml(doc.to_string())
    assert errors == []


def test_structure_basics():
    xml = build_sample_doc().to_string()
    assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert "<version>0.6.8</version>" in xml
    assert '<draftBlock name="Test">' in xml
    assert "<modeling />" in xml or "<modeling/>" in xml
    assert "<pieces />" in xml or "<pieces/>" in xml


def test_increment_requires_hash_prefix():
    doc = Document()
    with pytest.raises(ValueError):
        doc.add_increment("Width", 10)


def test_bad_line_type_rejected():
    doc = Document()
    block = doc.add_draft_block("T")
    a = block.add_base_point("A")
    with pytest.raises(ValueError):
        block.add_end_line_point("B", base=a, angle=0, length=10, line_type="wavy")


def test_bad_unit_rejected():
    with pytest.raises(ValueError):
        Document(unit="meters")
