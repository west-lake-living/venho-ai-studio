"""Deterministic naturalness checks for the M03 content validator.

This package deliberately contains no model/provider calls.  It turns common
Vietnamese AI-writing signals into repeatable, testable violations that M05
can act on during a rewrite.
"""

from validator_studio.naturalness.gate import evaluate_naturalness
from validator_studio.naturalness.report import NaturalnessReport, Violation

__all__ = ["NaturalnessReport", "Violation", "evaluate_naturalness"]
