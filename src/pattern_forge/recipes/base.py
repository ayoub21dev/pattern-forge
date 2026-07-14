"""Recipe interface: what every garment template must provide."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..sm2d import Document


@dataclass(frozen=True)
class MeasurementSpec:
    """One required body measurement with a plausible human range (same unit as the recipe)."""

    name: str
    min_value: float
    max_value: float
    description: str = ""

    def check(self, value: float) -> str | None:
        """Return an error message if the value is outside the plausible range."""
        if not (self.min_value <= value <= self.max_value):
            return (
                f"{self.name}={value:g} is outside the plausible range "
                f"[{self.min_value:g}, {self.max_value:g}] {self.description}".rstrip()
            )
        return None


@dataclass(frozen=True)
class OptionSpec:
    """One style option with a default and safe bounds."""

    name: str
    default: float
    min_value: float
    max_value: float
    description: str = ""


class Recipe(ABC):
    """A parametric garment template.

    Subclasses set `name`, `description`, `required_measurements`, `options`
    and implement `build()`. All values are in centimeters unless stated.
    """

    name: str = ""
    description: str = ""
    required_measurements: list[MeasurementSpec] = []
    options: list[OptionSpec] = []

    def default_options(self) -> dict[str, float]:
        return {o.name: o.default for o in self.options}

    def merged_options(self, options: dict[str, float] | None = None) -> dict[str, float]:
        """Provided options merged over the defaults — always a complete dict.

        Subclasses' check_inputs/build must read option values through this
        (never raw `options[...]`) so a partial dict can never raise KeyError.
        """
        return self.default_options() | dict(options or {})

    def check_inputs(
        self, measurements: dict[str, float], options: dict[str, float] | None = None
    ) -> list[str]:
        """Validate inputs BEFORE drawing anything. Returns error list; [] = good.

        Contract: this method returns errors — it never raises, even on a
        partial options dict.
        """
        options = dict(options or {})
        errors: list[str] = []
        for spec in self.required_measurements:
            if spec.name not in measurements:
                errors.append(f"missing measurement: {spec.name} ({spec.description})".rstrip())
                continue
            error = spec.check(measurements[spec.name])
            if error:
                errors.append(error)
        known_options = {o.name: o for o in self.options}
        for key, value in options.items():
            spec = known_options.get(key)
            if spec is None:
                errors.append(f"unknown option: {key}")
            elif not (spec.min_value <= value <= spec.max_value):
                errors.append(
                    f"option {key}={value:g} is outside the safe range "
                    f"[{spec.min_value:g}, {spec.max_value:g}]"
                )
        return errors

    def draft(
        self,
        measurements: dict[str, float],
        options: dict[str, float] | None = None,
    ) -> Document:
        """Validate inputs then build the pattern. The single public entry point."""
        merged = self.merged_options(options)
        errors = self.check_inputs(measurements, merged)
        if errors:
            raise ValueError("invalid inputs:\n- " + "\n- ".join(errors))
        return self.build(measurements, merged)

    @abstractmethod
    def build(self, measurements: dict[str, float], options: dict[str, float]) -> Document:
        """Draw the pattern. Called with validated inputs only."""
