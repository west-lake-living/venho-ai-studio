from __future__ import annotations

import re
from pathlib import Path

from validator_studio.naturalness import evaluate_naturalness
from validator_studio.naturalness.dna_leak_check import check_dna_leak


ROOT = Path(__file__).resolve().parents[2]


def _fixture(name: str) -> list[str]:
    text = (ROOT / "tests" / "fixtures" / name).read_text(encoding="utf-8")
    return [item.strip() for item in re.findall(r"^## \d+\n(.+?)(?=^## \d+|\Z)", text, flags=re.M | re.S)]


# Calibration fixtures are REAL data (2026-09-09 P2 pass), not agent-authored:
#   ai_sounding_vi.md    -> 34 published M05 captions the operator labelled
#                           "sounds like AI / generic"
#   human_written_vi.md  -> 12 captions labelled "fine" + 9 hand-written
#                           Voice Corpus paragraphs
# Do not edit the fixtures or relax a threshold to make a test pass.


def test_does_not_flag_acceptable_human_text() -> None:
    """The false-positive gate: none of the operator-approved captions or the
    hand-written Voice Corpus may be flagged (spec risk #1, <=10% budget)."""
    samples = _fixture("human_written_vi.md")
    assert len(samples) >= 20
    flagged = [s[:60] for s in samples if evaluate_naturalness(s).verdict != "PASS"]
    assert not flagged, f"gate flagged human-acceptable text: {flagged}"


def test_dna_token_leak_is_always_caught() -> None:
    """The one clean deterministic signal in the real data: a hex colour code
    or English scene descriptors leaking from the image/scene prompt into the
    published Vietnamese caption. 14/34 AI-sounding captions, 0 acceptable ones."""
    samples = _fixture("ai_sounding_vi.md")
    leaking = [s for s in samples if check_dna_leak(s)]
    assert len(leaking) >= 10
    missed = [s[:60] for s in leaking if evaluate_naturalness(s).verdict == "PASS"]
    assert not missed, f"DNA-leak caption passed the gate: {missed}"


def test_catches_a_meaningful_share_of_ai_sounding_captions() -> None:
    """Isolated (single-candidate) deterministic detection on real captions.

    Ceiling note: on this corpus the operator's AI/fine split is largely a
    voice judgement with no clean deterministic boundary -- the acceptable
    captions repeat the same scenes and structure almost as much as the bad
    ones. Closing the rest of the gap is the job of the material layer
    (U1 Local Beat, U2 Weekly Theme) and prompt fixes, not more rules here.
    The Repetition Guard lifts this materially once real recent posts are
    supplied in production (see daily_cycle `_recent_post_texts`)."""
    samples = _fixture("ai_sounding_vi.md")
    caught = sum(evaluate_naturalness(s).verdict != "PASS" for s in samples)
    assert caught / len(samples) >= 0.5


def test_repetition_guard_lifts_detection_with_recent_history() -> None:
    """With the 12 preceding captions supplied (production behaviour), the
    de-scaffolded 6-gram repetition check pushes near-duplicate captions over
    the line without flagging the whole feed."""
    samples = _fixture("ai_sounding_vi.md")
    caught = sum(
        evaluate_naturalness(s, recent_posts=samples[max(0, i - 12):i]).verdict != "PASS"
        for i, s in enumerate(samples)
    )
    # ~79% here; the fixture is AI captions only so the early samples have
    # little "recent history" to compare against. On the full mixed feed
    # (measured 2026-09-09) this reached ~91%.
    assert caught / len(samples) >= 0.75
