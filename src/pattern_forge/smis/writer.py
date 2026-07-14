"""In-memory model + XML writer for individual measurement files (.smis).

Targets format version 0.3.4 — the version used by the measurement samples
shipped with Seamly2D. Structure (see samples/measurements/individual/*.smis):

    <smis>
        <version>0.3.4</version>
        <read-only>false</read-only>
        <notes/>
        <unit>cm</unit>
        <pm_system>998</pm_system>
        <personal>...</personal>
        <body-measurements>
            <m name="waist_circ" value="84"/>
            ...
        </body-measurements>
    </smis>

Measurement names must be Seamly2D's known measurement codes (e.g. waist_circ,
hip_circ, height_knee ...) or custom names prefixed with '@'.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from ..xmlio import fmt_value, save_xml, serialize_xml

FORMAT_VERSION = "0.3.4"

#: pm_system 998 = "None" (no predefined patternmaking system)
DEFAULT_PM_SYSTEM = "998"


class MeasurementsFile:
    """A whole .smis individual measurements file."""

    def __init__(self, unit: str = "cm", notes: str = ""):
        if unit not in ("mm", "cm", "inch"):
            raise ValueError(f"unit must be mm/cm/inch, got {unit!r}")
        self.unit = unit
        self.notes = notes
        self.pm_system = DEFAULT_PM_SYSTEM
        # personal block (all optional for our purposes)
        self.family_name = ""
        self.given_name = ""
        self.birth_date = "1800-01-01"
        self.gender = "unknown"  # male | female | unknown
        self.email = ""
        self._measurements: dict[str, float] = {}

    def set(self, name: str, value: float) -> None:
        """Set one measurement value (e.g. set("waist_circ", 84))."""
        if not name:
            raise ValueError("measurement name must not be empty")
        self._measurements[name] = float(value)

    def set_many(self, values: dict[str, float]) -> None:
        for name, value in values.items():
            self.set(name, value)

    def get(self, name: str) -> float | None:
        return self._measurements.get(name)

    @property
    def names(self) -> list[str]:
        return list(self._measurements)

    # ---------------------------------------------------------------- output

    def to_element(self) -> ET.Element:
        root = ET.Element("smis")
        root.append(ET.Comment("Measurements created with pattern-forge (SeamlyMe-compatible)."))
        ET.SubElement(root, "version").text = FORMAT_VERSION
        ET.SubElement(root, "read-only").text = "false"
        ET.SubElement(root, "notes").text = self.notes or None
        ET.SubElement(root, "unit").text = self.unit
        ET.SubElement(root, "pm_system").text = self.pm_system
        personal = ET.SubElement(root, "personal")
        ET.SubElement(personal, "family-name").text = self.family_name or None
        ET.SubElement(personal, "given-name").text = self.given_name or None
        ET.SubElement(personal, "birth-date").text = self.birth_date
        ET.SubElement(personal, "gender").text = self.gender
        ET.SubElement(personal, "email").text = self.email or None
        body = ET.SubElement(root, "body-measurements")
        for name, value in self._measurements.items():
            ET.SubElement(body, "m", {"name": name, "value": fmt_value(value)})
        return root

    def to_string(self) -> str:
        return serialize_xml(self.to_element())

    def save(self, path: str | Path) -> Path:
        return save_xml(self.to_element(), path)
