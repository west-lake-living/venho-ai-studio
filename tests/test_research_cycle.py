"""Automated research cycle: question -> vault notes -> proposals -> decision.

Every test injects its collector and extractor; nothing here calls Tavily or
Gemini.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
import yaml

from research_engine.adapters.vault_reader import VaultReader
from research_engine.application.decide_proposed_fact import approve_proposed_fact, reject_proposed_fact
from research_engine.application.extract_facts import extract_fact_proposals
from research_engine.application.run_research_cycle import run_all_research_cycles, run_research_cycle
from shared.storage.proposed_fact_store import PENDING, ProposedFactStore, proposal_id

ROOT = Path(__file__).resolve().parents[1]
REAL_CONFIG_ROOT = ROOT / "config/projects/venho_hotel/research"


def _config_root(tmp_path: Path, domains: dict) -> Path:
    config_root = tmp_path / "config"
    config_root.mkdir(parents=True, exist_ok=True)
    (config_root / "research_questions.yaml").write_text(
        yaml.safe_dump({"version": 1, "domains": domains}, allow_unicode=True), encoding="utf-8"
    )
    return config_root


def _fake_tavily(results: list[dict]):
    def http_post(url, *, json=None, headers=None, timeout=None):  # noqa: ANN001, A002
        return {"results": results}

    return http_post


_TWO_RESULTS = [
    {"url": "https://example.com/a", "title": "Hotel A", "content": "Giá phòng từ 900,000đ", "score": 0.9},
    {"url": "https://example.com/b", "title": "Hotel B", "content": "Giá phòng từ 1,200,000đ", "score": 0.8},
]


def _competitor_config(tmp_path: Path) -> Path:
    return _config_root(
        tmp_path,
        {"competitor": {"question": "Đối thủ định giá thế nào?", "collector": "tavily", "queries": ["q1"], "max_results": 5}},
    )


# --- the guardrail ---------------------------------------------------------


def test_a_domain_without_a_written_question_refuses_to_run(tmp_path: Path) -> None:
    """§6.7's guardrail is a refusal in code, not a paragraph in a doc."""
    config_root = _config_root(tmp_path, {"competitor": {"question": "   ", "collector": "tavily"}})

    with pytest.raises(ValueError, match="written research question"):
        run_research_cycle("competitor", config_root=config_root, vault_root=tmp_path / "vault")


def test_an_unregistered_domain_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no entry"):
        run_research_cycle("made_up", config_root=_competitor_config(tmp_path), vault_root=tmp_path / "vault")


# --- the cycle -------------------------------------------------------------


def test_cycle_writes_r0_source_notes_and_one_r2_synthesis_into_the_vault(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    result = run_research_cycle(
        "competitor",
        config_root=_competitor_config(tmp_path),
        vault_root=vault,
        data_root=tmp_path / "data",
        tavily_api_key="fake",
        gemini_api_key="",
        http_post=_fake_tavily(_TWO_RESULTS),
        extract_fn=lambda **kwargs: [],
        today=date(2026, 8, 6),
    )

    assert result.ran
    assert result.sources_collected == 2
    assert len(result.source_notes) == 2

    reader = VaultReader(vault)
    for note_path in result.source_notes:
        frontmatter = reader.read_frontmatter(Path(note_path))
        assert frontmatter["evidence_level"] == "R0"
        assert frontmatter["domain"] == "competitor"
        assert frontmatter["verified_by_human"] is False

    synthesis = reader.read_frontmatter(Path(result.synthesis_note))
    assert synthesis["evidence_level"] == "R2"
    assert Path(result.synthesis_note).read_text(encoding="utf-8").count("Đối thủ định giá thế nào?") == 1


def test_the_same_page_returned_by_two_queries_becomes_one_source_note(tmp_path: Path) -> None:
    """Duplicate sources would inflate the evidence standing behind a proposal."""
    config_root = _config_root(
        tmp_path,
        {"competitor": {"question": "Đối thủ định giá thế nào?", "collector": "tavily", "queries": ["q1", "q2"]}},
    )
    result = run_research_cycle(
        "competitor", config_root=config_root, vault_root=tmp_path / "vault", data_root=tmp_path / "data",
        tavily_api_key="fake", gemini_api_key="", http_post=_fake_tavily(_TWO_RESULTS),
        extract_fn=lambda **kwargs: [], today=date(2026, 8, 6),
    )

    assert result.sources_collected == 2  # not 4


def test_cycle_is_reported_as_skipped_rather_than_failed_without_an_api_key(tmp_path: Path) -> None:
    result = run_research_cycle(
        "competitor", config_root=_competitor_config(tmp_path), vault_root=tmp_path / "vault",
        data_root=tmp_path / "data", tavily_api_key="", gemini_api_key="",
    )

    assert result.ran is False
    assert "TAVILY_API_KEY" in result.skipped_reason


def test_manual_collector_domain_ingests_the_file_harry_exports(tmp_path: Path) -> None:
    """Scraping OTA reviews is forbidden (§7.2), so guest_voice runs off an export."""
    config_root = _config_root(tmp_path, {"guest_voice": {"question": "Khách khen chê gì?", "collector": "manual"}})
    export = tmp_path / "agoda_reviews.txt"
    export.write_text("Phòng sạch, view hồ đẹp. Thang máy hơi chậm.", encoding="utf-8")

    result = run_research_cycle(
        "guest_voice", config_root=config_root, vault_root=tmp_path / "vault", data_root=tmp_path / "data",
        input_file=export, gemini_api_key="", extract_fn=lambda **kwargs: [], today=date(2026, 8, 6),
    )

    assert result.ran
    assert result.sources_collected == 1
    assert "view hồ đẹp" in Path(result.source_notes[0]).read_text(encoding="utf-8")


def test_manual_domain_without_a_file_is_skipped_not_invented(tmp_path: Path) -> None:
    config_root = _config_root(tmp_path, {"guest_voice": {"question": "Khách khen chê gì?", "collector": "manual"}})

    result = run_research_cycle(
        "guest_voice", config_root=config_root, vault_root=tmp_path / "vault", data_root=tmp_path / "data"
    )

    assert result.ran is False
    assert "input-file" in result.skipped_reason


def test_run_all_reports_every_domain_including_the_ones_waiting_on_a_human(tmp_path: Path) -> None:
    config_root = _config_root(
        tmp_path,
        {
            "competitor": {"question": "Q1", "collector": "tavily", "queries": ["q"]},
            "guest_voice": {"question": "Q2", "collector": "manual"},
        },
    )
    results = run_all_research_cycles(
        config_root=config_root, vault_root=tmp_path / "vault", data_root=tmp_path / "data",
        tavily_api_key="fake", gemini_api_key="", http_post=_fake_tavily(_TWO_RESULTS),
        extract_fn=lambda **kwargs: [], today=date(2026, 8, 6),
    )

    by_domain = {r.domain: r for r in results}
    assert by_domain["competitor"].ran is True
    assert by_domain["guest_voice"].ran is False  # surfaced, not silently dropped


# --- proposals -------------------------------------------------------------


_ONE_PROPOSAL = [
    {
        "fact_key": "competitor.avg_rate_westlake",
        "value": "900,000đ",
        "value_type": "string",
        "rationale": "Nguồn nêu giá phòng từ 900,000đ",
        "source_index": 0,
        "source_uri": "https://example.com/a",
        "source_title": "Hotel A",
    }
]


def test_cycle_queues_proposals_as_pending_never_as_facts(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    result = run_research_cycle(
        "competitor", config_root=_competitor_config(tmp_path), vault_root=tmp_path / "vault", data_root=data_root,
        tavily_api_key="fake", gemini_api_key="fake", http_post=_fake_tavily(_TWO_RESULTS),
        extract_fn=lambda **kwargs: list(_ONE_PROPOSAL), today=date(2026, 8, 6),
    )

    assert result.proposals_created == 1
    items = ProposedFactStore(data_root=data_root).list_items()
    assert [item["status"] for item in items] == [PENDING]
    # No fact was written anywhere.
    assert list((data_root / "venho_hotel" / "growth" / "facts").glob("*.json")) == []


def test_rerunning_a_cycle_does_not_resurrect_a_rejected_proposal(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    config_root = _competitor_config(tmp_path)
    kwargs = dict(
        config_root=config_root, vault_root=tmp_path / "vault", data_root=data_root, tavily_api_key="fake",
        gemini_api_key="fake", http_post=_fake_tavily(_TWO_RESULTS),
        extract_fn=lambda **kw: list(_ONE_PROPOSAL), today=date(2026, 8, 6),
    )
    run_research_cycle("competitor", **kwargs)
    store = ProposedFactStore(data_root=data_root)
    reject_proposed_fact(
        proposal_id("competitor", "competitor.avg_rate_westlake", "900,000đ"),
        rejected_by="harry", reason="giá đã cũ", data_root=data_root,
    )

    result = run_research_cycle("competitor", **kwargs)

    assert result.proposals_created == 0
    assert [item["status"] for item in store.list_items()] == ["rejected"]


def test_a_failing_extractor_still_leaves_the_vault_notes_behind(tmp_path: Path) -> None:
    """The notes are the durable output; the extraction is a convenience."""

    def boom(**kwargs):  # noqa: ANN001, ANN003
        raise RuntimeError("gemini down")

    result = run_research_cycle(
        "competitor", config_root=_competitor_config(tmp_path), vault_root=tmp_path / "vault",
        data_root=tmp_path / "data", tavily_api_key="fake", gemini_api_key="fake",
        http_post=_fake_tavily(_TWO_RESULTS), extract_fn=boom, today=date(2026, 8, 6),
    )

    assert result.ran
    assert len(result.source_notes) == 2
    assert result.proposals_created == 0


# --- the decision ----------------------------------------------------------


def _seed_pending(tmp_path: Path) -> tuple[Path, str]:
    data_root = tmp_path / "data"
    result = run_research_cycle(
        "competitor", config_root=_competitor_config(tmp_path), vault_root=tmp_path / "vault", data_root=data_root,
        tavily_api_key="fake", gemini_api_key="fake", http_post=_fake_tavily(_TWO_RESULTS),
        extract_fn=lambda **kw: list(_ONE_PROPOSAL), today=date(2026, 8, 6),
    )
    return data_root, result.proposals[0]["id"]


def test_approving_a_proposal_creates_a_real_r3_fact(tmp_path: Path) -> None:
    data_root, pid = _seed_pending(tmp_path)

    result = approve_proposed_fact(
        pid, approved_by="harry", data_root=data_root, vault_root=tmp_path / "vault"
    )

    fact = json.loads(Path(result["fact_path"]).read_text(encoding="utf-8"))
    assert fact["fact_key"] == "competitor.avg_rate_westlake"
    assert fact["status"] == "approved"
    assert fact["approved_by"] == "harry"
    assert ProposedFactStore(data_root=data_root).get(pid)["status"] == "approved"


def test_approval_requires_a_named_human(tmp_path: Path) -> None:
    data_root, pid = _seed_pending(tmp_path)

    with pytest.raises(ValueError, match="approve itself"):
        approve_proposed_fact(pid, approved_by="  ", data_root=data_root, vault_root=tmp_path / "vault")


def test_the_same_proposal_cannot_be_decided_twice(tmp_path: Path) -> None:
    data_root, pid = _seed_pending(tmp_path)
    reject_proposed_fact(pid, rejected_by="harry", data_root=data_root)

    with pytest.raises(ValueError, match="already rejected"):
        reject_proposed_fact(pid, rejected_by="harry", data_root=data_root)


def test_approval_cannot_promote_from_a_non_r2_note(tmp_path: Path) -> None:
    """The approval UI must not become a way around the Evidence Ladder:
    PromotionPolicy still refuses anything that is not an R2 synthesis."""
    data_root, pid = _seed_pending(tmp_path)
    store = ProposedFactStore(data_root=data_root)
    items = store.load()
    # Point the proposal at one of its own R0 source notes instead.
    items[0]["synthesis_note"] = str(next((tmp_path / "vault" / "sources").rglob("*.md")))
    store._save(items)

    with pytest.raises(ValueError, match="Only R2"):
        approve_proposed_fact(pid, approved_by="harry", data_root=data_root, vault_root=tmp_path / "vault")


# --- extraction hardening --------------------------------------------------


def test_extractor_drops_entries_that_miss_the_schema() -> None:
    """Fail-closed: a malformed entry yields fewer proposals, never a
    lower-quality one that reaches Harry looking legitimate."""
    response = json.dumps(
        [
            {"fact_key": "competitor.rate", "value": "900k", "value_type": "string", "rationale": "ok", "source_index": 0},
            {"fact_key": "../../etc/passwd", "value": "x", "value_type": "string", "source_index": 0},
            {"fact_key": "competitor.bad_type", "value": "x", "value_type": "essay", "source_index": 0},
            {"fact_key": "competitor.out_of_range", "value": "x", "value_type": "string", "source_index": 99},
            {"fact_key": "competitor.empty", "value": "   ", "value_type": "string", "source_index": 0},
        ],
        ensure_ascii=False,
    )

    proposals = extract_fact_proposals(
        question="Đối thủ định giá thế nào?",
        sources=[{"title": "A", "source_uri": "https://example.com/a", "snippet": "..."}],
        api_key="fake",
        client_fn=lambda **kwargs: response,
    )

    assert [p["fact_key"] for p in proposals] == ["competitor.rate"]


def test_extractor_returns_nothing_when_the_model_answers_with_junk() -> None:
    proposals = extract_fact_proposals(
        question="Q", sources=[{"title": "A", "source_uri": "u", "snippet": "s"}],
        api_key="fake", client_fn=lambda **kwargs: "I cannot help with that",
    )

    assert proposals == []


def test_extractor_truncates_long_pages_before_sending_them(tmp_path: Path) -> None:
    """Long scraped pages are both the injection surface and the token cost."""
    captured = {}

    def client_fn(*, model, system, contents):  # noqa: ANN001
        captured["contents"] = contents
        return "[]"

    extract_fact_proposals(
        question="Q",
        sources=[{"title": "A", "source_uri": "u", "snippet": "x" * 50_000}],
        api_key="fake",
        client_fn=client_fn,
    )

    assert len(json.loads(captured["contents"])["sources"][0]["snippet"]) == 1200


def test_extractor_requires_a_question() -> None:
    with pytest.raises(ValueError, match="one written question"):
        extract_fact_proposals(question="  ", sources=[{"title": "A"}], api_key="fake", client_fn=lambda **k: "[]")


# --- the real config -------------------------------------------------------


def test_every_registered_domain_has_a_written_question() -> None:
    """DoD #14 counts 9 domains; a domain with no question can never run."""
    domains = yaml.safe_load((REAL_CONFIG_ROOT / "domains.yaml").read_text(encoding="utf-8"))["domains"]
    questions = yaml.safe_load((REAL_CONFIG_ROOT / "research_questions.yaml").read_text(encoding="utf-8"))["domains"]

    assert set(questions) == set(domains)
    for domain, config in questions.items():
        assert config.get("question", "").strip(), f"{domain} has no written question"
