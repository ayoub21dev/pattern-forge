"""Parametric garment recipes — the encoded patternmaking knowledge.

Each recipe declares the measurements it needs (with sane human ranges) and
builds a Seamly2D document from (measurements + options). Recipes never invent
free geometry: they implement a documented drafting method.
"""

from .base import MeasurementSpec, Recipe
from .aline_skirt import AlineSkirt

__all__ = ["Recipe", "MeasurementSpec", "AlineSkirt"]
