"""FORBIDDEN hygiene.

FORBIDDEN is policy: a list of things that must never be generated. The vision model,
asked for "things clearly NOT present", answers with bare feature names as often as with
prohibitions — the `outside` DNA ended up listing "lake view", "railing", "Rooftop terrace"
and "Cityscape" as forbidden. Those are the subject's own selling points, and one overlay
that forgot to restate its curated block was enough to turn them live and fail a good
rooftop image on "lake view" (measured 2026-08-07: forbidden category 100 → 0).

A prohibition is recognisable without a model: it negates. Anything that does not is a
feature name that slipped through, and is dropped rather than stored as policy.
"""

from __future__ import annotations

import re

# Leading negation in the wording the observe prompts ask for (English only by contract —
# see the "English values rule" in CLAUDE.md).
_NEGATION_PREFIX = re.compile(
    r"^\s*(no\b|not\b|never\b|without\b|avoid\b|exclude\b|absolutely\s+no\b|do\s+not\b|don't\b)",
    re.IGNORECASE,
)


def is_prohibition(rule: str) -> bool:
    """True when `rule` states something that must not appear, rather than naming a feature."""
    return bool(rule and _NEGATION_PREFIX.match(rule))


def sanitize_forbidden(rules: list[str]) -> list[str]:
    """Drop non-prohibitions and case-insensitive duplicates, preserving order."""
    kept: list[str] = []
    seen: set[str] = set()
    for rule in rules:
        if not is_prohibition(rule):
            continue
        key = " ".join(rule.strip().lower().split())
        if key in seen:
            continue
        seen.add(key)
        kept.append(rule)
    return kept
