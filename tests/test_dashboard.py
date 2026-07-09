from __future__ import annotations

import importlib
import json
from pathlib import Path

import yaml

from dashboard import MODULE_ID
from dashboard.gateway import DashboardGateway, build_dashboard_snapshot, face_gate_status


def test_dashboard_imports_and_scaffold_exists() -> None:
    module = importlib.import_module("dashboard")
    root = Path("dashboard")

    assert module.MODULE_ID == "M10"
    assert MODULE_ID == "M10"
    assert (root / "gateway.py").exists()


def test_face_lock_gate_thresholds_match_module_10_plan() -> None:
    assert face_gate_status(9.1) == "APPROVED"
    assert face_gate_status(8.4) == "CONDITIONAL"
    assert face_gate_status(7.9) == "REJECT"
    assert face_gate_status(88.0) == "CONDITIONAL"
    assert face_gate_status(None) == "NOT_AVAILABLE"


def test_dashboard_snapshot_reads_existing_repo_artifacts_offline() -> None:
    snapshot = build_dashboard_snapshot(Path("."), project="venho_hotel")

    assert snapshot.project.display_name == "Ven Hồ Hotel"
    assert snapshot.project.prompt_name == "Ven Ho Hotel"
    assert {"lake_view_room", "deluxe_double", "lobby", "facade", "linh_an", "westlake", "outside"} <= {
        item.subject for item in snapshot.subjects
    }
    assert snapshot.system["zero_live_api_calls"] is True
    assert snapshot.system["counts"]["subjects"] >= 7
    assert snapshot.agent_personas


def test_dashboard_degrades_by_module_without_crashing(tmp_path: Path) -> None:
    project_root = tmp_path / "repo"
    subjects_dir = project_root / "config" / "projects" / "venho_hotel" / "subjects"
    agents_dir = project_root / "config" / "projects" / "venho_hotel" / "agents"
    subjects_dir.mkdir(parents=True)
    agents_dir.mkdir(parents=True)
    (subjects_dir / "linh_an.yaml").write_text("subject: linh_an\n", encoding="utf-8")
    (agents_dir / "marketing_agent.yaml").write_text(
        yaml.safe_dump({"display_name": "Ven Hồ Hotel Marketing Agent", "allowed_modules": ["M04"]}),
        encoding="utf-8",
    )

    snapshot = DashboardGateway(project_root, "venho_hotel").build_snapshot()

    assert snapshot.project.display_name == "Ven Hồ Hotel"
    assert any(advisory.module == "M01" for advisory in snapshot.advisories)
    assert any(advisory.module == "M06" for advisory in snapshot.advisories)
    assert any(advisory.module == "M07" for advisory in snapshot.advisories)
    assert snapshot.agent_personas[0]["agent"] == "marketing_agent"


def test_dashboard_reads_validation_face_gate_from_fixture(tmp_path: Path) -> None:
    manifest = {
        "runs": [
            {
                "project": "venho_hotel",
                "subject": "linh_an",
                "validation_type": "face",
                "overall_score": 92,
                "verdict": "approve",
            }
        ]
    }
    path = tmp_path / "data" / "projects" / "venho_hotel" / "validation"
    path.mkdir(parents=True)
    (path / "validation_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    runs = DashboardGateway(tmp_path, "venho_hotel").validation_runs()

    assert runs[0]["face_lock_gate"] == "APPROVED"
