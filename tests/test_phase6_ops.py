from __future__ import annotations

import json
from pathlib import Path

import pytest

from automation_studio.ai_studio_port import get_capability, list_capabilities
from automation_studio.job_contract import JobContract, JobTransitionError
from automation_studio.living_lab import LivingLabRun, record_run, summarize_runs
from automation_studio.adapters import wardrobe_adapter
from agent_studio.agents import base_agent as base_agent_module
from agent_studio.agents import BaseAgent


def test_job_contract_keeps_approval_execute_publish_separate() -> None:
    job = JobContract(job_id="job_001", capability="publish_content", project="venho_hotel")

    with pytest.raises(JobTransitionError):
        job.transition("published", actor="harry")

    approved = job.transition("approved", actor="harry", note="manual approval")
    executed = approved.transition("executed", actor="system", note="dry run")
    published = executed.transition("published", actor="harry", note="publish confirmed")

    assert approved.approval is not None
    assert executed.execution is not None
    assert published.publication is not None
    assert [entry["to"] for entry in published.audit] == ["approved", "executed", "published"]


def test_ai_studio_port_exposes_coarse_capabilities() -> None:
    ids = {capability.id for capability in list_capabilities()}

    assert {"wardrobe_ingest", "content_generate", "video_package", "publish_content"} <= ids
    assert get_capability("wardrobe_ingest").requires_approval is True


def test_wardrobe_ingest_blocks_index_update_on_validation_fail(tmp_path: Path, monkeypatch) -> None:
    base = tmp_path
    source = base / "data/projects/linh_an/wardrobe/new_outfit"
    source.mkdir(parents=True)
    (source / "image.png").write_text("fake", encoding="utf-8")
    index_dir = base / "config/projects/linh_an"
    index_dir.mkdir(parents=True)
    (index_dir / "wardrobe_index.json").write_text(
        json.dumps({"schema_version": "1.0", "project": "linh_an", "families": [], "outfits": []}),
        encoding="utf-8",
    )
    monkeypatch.setattr(wardrobe_adapter, "BASE_DIR", base)

    result = wardrobe_adapter.wardrobe_ingest(
        outfit_id="new_outfit",
        source_dir="data/projects/linh_an/wardrobe/new_outfit",
        schema_subject="outfit_e_sport",
        display_label="New Outfit",
        validation_status="fail",
    )

    assert result.status == "failed"
    assert result.data["index_update_blocked"] is True
    assert json.loads((index_dir / "wardrobe_index.json").read_text(encoding="utf-8"))["outfits"] == []


def test_wardrobe_index_update_requires_human_approval(tmp_path: Path, monkeypatch) -> None:
    base = tmp_path
    index_dir = base / "config/projects/linh_an"
    index_dir.mkdir(parents=True)
    (index_dir / "wardrobe_index.json").write_text(
        json.dumps({
            "schema_version": "1.0",
            "project": "linh_an",
            "updated_at": "2026-07-16",
            "families": [{"family_key": "sport_active", "outfit_ids": []}],
            "outfits": [],
        }),
        encoding="utf-8",
    )
    review = base / "review.json"
    review.write_text(
        json.dumps({
            "outfit_id": "new_outfit",
            "family_key": "sport_active",
            "schema_subject": "outfit_e_sport",
            "display_label": "New Outfit",
            "source_dir": "data/projects/linh_an/wardrobe/new_outfit",
            "description": "test outfit",
            "validation_status": "pass",
            "approved_for_index": False,
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(wardrobe_adapter, "BASE_DIR", base)

    with pytest.raises(ValueError, match="Human review not approved"):
        wardrobe_adapter.wardrobe_index_update(str(review))

    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["approved_for_index"] = True
    review.write_text(json.dumps(payload), encoding="utf-8")
    result = wardrobe_adapter.wardrobe_index_update(str(review))

    assert result.status == "success"
    index = json.loads((index_dir / "wardrobe_index.json").read_text(encoding="utf-8"))
    assert index["outfits"][0]["outfit_id"] == "new_outfit"


def test_m09_hard_stops_before_dispatch_when_knowledge_missing(monkeypatch) -> None:
    def fail_dispatch(*args, **kwargs):  # pragma: no cover - should never execute
        raise AssertionError("dispatch_to_automation must not be called")

    monkeypatch.setattr(base_agent_module, "dispatch_to_automation", fail_dispatch)
    response = BaseAgent().run({
        "project": "venho_hotel",
        "agent": "marketing_agent",
        "goal": "Tạo campaign nhưng thiếu knowledge",
        "context": {"knowledge_refs": []},
        "constraints": {"language": "vi", "validation_level": "strict", "max_steps": 3, "allow_external_actions": False},
        "execution_mode": "execute",
        "use_mock_engine": True,
    })

    assert response.error_code == "ERR_MISSING_KNOWLEDGE"
    assert response.missing_knowledge
    assert any("M04 dispatch skipped" in line for line in response.execution_log)


def test_living_lab_records_operational_metrics(tmp_path: Path) -> None:
    record_run(LivingLabRun("run_a", True, True, 0, 20, 0.12, "continue"), root=tmp_path)
    record_run(LivingLabRun("run_b", False, False, 2, 8, 0.08, "simplify"), root=tmp_path)

    summary = summarize_runs([
        LivingLabRun(**json.loads((tmp_path / "run_a.json").read_text(encoding="utf-8"))),
        LivingLabRun(**json.loads((tmp_path / "run_b.json").read_text(encoding="utf-8"))),
    ])

    assert summary["runs"] == 2
    assert summary["outputs_used"] == 1
    assert summary["first_try_approval_rate"] == 0.5
    assert summary["total_retries"] == 2
    assert summary["latest_decision"] == "simplify"
