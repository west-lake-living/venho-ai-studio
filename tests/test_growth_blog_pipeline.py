from __future__ import annotations

from pathlib import Path
from shutil import copyfile

from knowledge_studio.facts.fact_resolver import FactResolver
from knowledge_studio.facts.fact_store import FactStore

from growth_orchestrator.application.run_blog_pipeline import run_blog_pipeline


def _tmp_data_root_with_westlake_dna(tmp_path: Path) -> Path:
    root = tmp_path / "data" / "projects"
    knowledge_dir = root / "venho_hotel" / "knowledge"
    knowledge_dir.mkdir(parents=True)
    copyfile(
        Path("data/projects/venho_hotel/knowledge/VENHO_HOTEL_WESTLAKE_DNA.json"),
        knowledge_dir / "VENHO_HOTEL_WESTLAKE_DNA.json",
    )
    return root


def test_run_blog_pipeline_with_no_approved_facts_generates_without_facts_paragraph(tmp_path: Path) -> None:
    data_root = _tmp_data_root_with_westlake_dna(tmp_path)
    resolver = FactResolver(project="venho_hotel", data_root=data_root)

    result = run_blog_pipeline(
        "Mot ngay o Ho Tay", keyword="khach san gan Ho Tay", data_root=data_root, fact_resolver=resolver
    )

    assert result["facts_cited"] == []
    assert result["title"]
    assert result["body"]


def test_run_blog_pipeline_cites_every_approved_seed_fact(tmp_path: Path) -> None:
    data_root = _tmp_data_root_with_westlake_dna(tmp_path)
    store = FactStore(project="venho_hotel", data_root=data_root)
    store.load_seed_facts(Path("config/projects/venho_hotel/growth/seed_facts.json"))
    resolver = FactResolver(project="venho_hotel", data_root=data_root)

    result = run_blog_pipeline(
        "Mot ngay o Ho Tay", keyword="khach san gan Ho Tay", data_root=data_root, fact_resolver=resolver
    )

    assert set(result["facts_cited"]) == {
        "hotel.room_count",
        "hotel.address",
        "hotel.website",
        "review.agoda_overall",
    }
    assert "12 phòng" in result["body"]
    assert "181 Nguyen Dinh Thi" in result["body"]
    assert "8.5/10" in result["body"]
    assert len(result["fact_source_rs_ids"]) == 4
    assert all(result["fact_source_rs_ids"])


def test_run_blog_pipeline_skips_unapproved_fact(tmp_path: Path) -> None:
    data_root = _tmp_data_root_with_westlake_dna(tmp_path)
    store = FactStore(project="venho_hotel", data_root=data_root)
    store.save(
        {
            "fact_key": "hotel.room_count",
            "value": 99,
            "value_type": "integer",
            "source_type": "owner_confirmed",
            "source_rs_id": "RS-fake",
            "confidence": 1.0,
            "valid_from": "2026-01-01T00:00:00+07:00",
            "valid_to": None,
            "status": "pending_approval",
            "version": 1,
        }
    )
    resolver = FactResolver(project="venho_hotel", data_root=data_root)

    result = run_blog_pipeline(
        "Mot ngay o Ho Tay", keyword="khach san gan Ho Tay", data_root=data_root, fact_resolver=resolver
    )

    assert "hotel.room_count" not in result["facts_cited"]
    assert "99 phòng" not in result["body"]
