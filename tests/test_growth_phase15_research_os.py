from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from knowledge_studio.facts.fact_resolver import FactResolver
from knowledge_studio.facts.fact_store import FactStore
from research_engine.adapters.frontmatter_validator import validate_frontmatter
from research_engine.adapters.notebooklm_handoff import NotebookLMHandoff
from research_engine.adapters.vault_reader import VaultReader
from research_engine.application.collect_sources import collect_source_note, collect_structured_note
from research_engine.application.detect_stale_knowledge import detect_stale_facts, revoke_approvals_for_expired_facts
from research_engine.application.propose_fact import propose_fact
from research_engine.application.synthesize_notes import synthesize_notes
from research_engine.domain.evidence_level import EvidenceLevel, can_transition
from research_engine.domain.promotion_policy import PromotionPolicy
from research_engine.domain.research_note import ResearchNote


def test_evidence_ladder_blocks_r2t_to_r3_and_requires_human_for_r2() -> None:
    assert can_transition(EvidenceLevel.R2, EvidenceLevel.R3, human_approved=False) is False
    assert can_transition(EvidenceLevel.R2, EvidenceLevel.R3, human_approved=True) is True
    assert can_transition(EvidenceLevel.R2_T, EvidenceLevel.R3, human_approved=True) is False


def test_frontmatter_validator_accepts_repo_seed_note() -> None:
    note = validate_frontmatter(Path("research/insights/RS-2026-08-0014_guest_voice_synthesis.md"))
    assert note.rs_id == "RS-2026-08-0014"
    assert note.evidence_level is EvidenceLevel.R2


def test_question_collect_synth_promote_to_r3_fact_roundtrip(tmp_path) -> None:
    vault_root = tmp_path / "research"
    source = collect_source_note(
        rs_id="RS-2026-08-0100",
        domain="guest_voice",
        source_uri="owner-confirmed",
        title="room-count",
        body="Ven Ho Hotel has 12 boutique rooms.",
        vault_root=vault_root,
    )
    structured = collect_structured_note(
        rs_id="RS-2026-08-0101",
        domain="guest_voice",
        source_uri="owner-confirmed",
        title="room-count-structured",
        observations=["12 boutique rooms"],
        vault_root=vault_root,
    )
    synthesis = synthesize_notes(
        rs_id="RS-2026-08-0102",
        domain="guest_voice",
        question="Which concrete proof point can support a trust-led brief?",
        source_paths=[source, structured],
        vault_root=vault_root,
    )
    frontmatter = VaultReader(vault_root).read_frontmatter(synthesis)
    note = ResearchNote.model_validate(frontmatter)
    fact = propose_fact(note, fact_key="hotel.room_count", value=12, value_type="integer", approved_by="harry")
    store = FactStore(data_root=tmp_path / "data")
    store.save(fact)

    resolved = FactResolver(data_root=tmp_path / "data").resolve("hotel.room_count")
    assert resolved is not None
    assert resolved["value"] == 12


def test_r2t_note_cannot_be_promoted_even_with_human() -> None:
    note = ResearchNote(
        rs_id="RS-2026-08-0200",
        type="trend",
        domain="social_trend",
        evidence_level=EvidenceLevel.R2_T,
        status="reviewed",
        collected_at=date.today(),
        confidence=0.95,
        expires_at=date.today() + timedelta(days=7),
    )
    decision = PromotionPolicy().evaluate(note, human_approved=True)
    assert decision.allowed is False
    assert "R2-T" in decision.reason


def test_stale_fact_detection_and_approval_revocation(tmp_path) -> None:
    store = FactStore(data_root=tmp_path / "data")
    store.save(
        {
            "fact_key": "review.agoda_overall",
            "value": "8.5/10",
            "value_type": "string",
            "source_type": "platform_verified",
            "source_rs_id": "RS-2026-08-0003",
            "confidence": 0.95,
            "valid_from": "2026-01-01T00:00:00+07:00",
            "valid_to": "2026-01-02T00:00:00+07:00",
            "status": "approved",
            "version": 1,
            "approved_by": "harry",
            "approved_at": "2026-01-01T00:00:00+07:00",
        }
    )
    expired = detect_stale_facts(data_root=tmp_path / "data", today=date(2026, 8, 3))
    approvals = revoke_approvals_for_expired_facts(
        [{"id": "approval-1", "status": "approved", "fact_keys": ["review.agoda_overall"]}],
        expired,
    )
    assert expired == ["review.agoda_overall"]
    assert approvals[0]["status"] == "revoked"


def test_notebooklm_handoff_requires_question_and_verifies_r2_export(tmp_path) -> None:
    handoff = NotebookLMHandoff(root=tmp_path / "research")
    with pytest.raises(ValueError):
        handoff.create_inbox("blank", "", [])
    folder = handoff.create_inbox("guest-proof", "What proof point matters?", ["owner-confirmed"])
    assert (folder / "question.md").exists()
    export = tmp_path / "research" / "synthesis" / "guest-proof.md"
    export.parent.mkdir(parents=True)
    export.write_text("---\nevidence_level: R2\nexpires_at: 2026-11-03\n---\n\nBody\n", encoding="utf-8")
    assert handoff.verify_export(export) is True
