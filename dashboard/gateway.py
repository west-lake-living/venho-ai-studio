"""Read-only data gateway for Module 10 Dashboard.

The dashboard layer must stay presentation-only. This module reads existing
module artifacts and config files, normalizes them for UI rendering, and never
recomputes core module verdicts or mutates production data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_PROJECT = "venho_hotel"
PROJECT_DISPLAY = {"venho_hotel": "Ven Hồ Hotel"}
PROJECT_PROMPT_DISPLAY = {"venho_hotel": "Ven Ho Hotel"}
EXPECTED_SUBJECTS = ("lake_view_room", "deluxe_double", "lobby", "facade", "linh_an", "westlake", "outside")


@dataclass(frozen=True)
class Advisory:
    module: str
    status: str
    message: str


@dataclass(frozen=True)
class ProjectSummary:
    project: str
    display_name: str
    prompt_name: str
    config_sections: list[str]


@dataclass(frozen=True)
class SubjectAsset:
    subject: str
    has_config: bool
    has_overrides: bool
    has_dna_json: bool
    has_dna_md: bool
    has_compact: bool
    manifest: str | None = None


@dataclass(frozen=True)
class DashboardSnapshot:
    project: ProjectSummary
    subjects: list[SubjectAsset]
    prompts: list[dict[str, Any]]
    content_items: list[dict[str, Any]]
    validation_runs: list[dict[str, Any]]
    automation_jobs: list[dict[str, Any]]
    video_items: list[dict[str, Any]]
    publishing_items: list[dict[str, Any]]
    analytics_items: list[dict[str, Any]]
    agent_personas: list[dict[str, Any]]
    system: dict[str, Any]
    advisories: list[Advisory] = field(default_factory=list)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def _latest_files(paths: list[Path], limit: int) -> list[Path]:
    existing = [path for path in paths if path.exists()]
    return sorted(existing, key=lambda p: p.stat().st_mtime, reverse=True)[:limit]


def _rel(path: str | Path | None, base_dir: Path) -> str | None:
    if not path:
        return None
    candidate = Path(path)
    try:
        return str(candidate.relative_to(base_dir))
    except ValueError:
        return str(candidate)


def face_gate_status(score: float | int | None) -> str:
    """Map an M03 face score into the dashboard's Face Lock gate labels."""
    if score is None:
        return "NOT_AVAILABLE"
    normalized = float(score) / 10 if float(score) > 10 else float(score)
    if normalized >= 9.0:
        return "APPROVED"
    if normalized >= 8.0:
        return "CONDITIONAL"
    return "REJECT"


class DashboardGateway:
    """Read-only adapter over M01-M09 artifacts."""

    def __init__(self, base_dir: Path | str = Path("."), project: str = DEFAULT_PROJECT) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.project = project
        self.config_root = self.base_dir / "config" / "projects" / project
        self.data_root = self.base_dir / "data" / "projects" / project

    def build_snapshot(self) -> DashboardSnapshot:
        advisories: list[Advisory] = []
        project = self.project_summary()
        subjects = self.subject_assets()
        prompts = self.prompt_items()
        content_items = self.content_items()
        validation_runs = self.validation_runs()
        automation_jobs = self.automation_jobs()
        video_items = self.video_items()
        publishing_items = self.publishing_items()
        analytics_items = self.analytics_items()
        agent_personas = self.agent_personas()

        missing_subjects = [item.subject for item in subjects if not item.has_dna_json]
        if missing_subjects:
            advisories.append(
                Advisory("M01", "degraded", f"Missing DNA JSON for: {', '.join(missing_subjects)}")
            )
        if not video_items:
            advisories.append(Advisory("M06", "degraded", "No video storyboard package found."))
        if not publishing_items:
            advisories.append(Advisory("M07", "degraded", "No publishing package or receipt found."))
        if not analytics_items:
            advisories.append(Advisory("M08", "advisory", "No analytics snapshot yet; UI remains read-only."))

        system = {
            "module": "dashboard",
            "contract": "presentation_only",
            "project": self.project,
            "token_usage": "read_from_system_monitor_when_available",
            "cache_status": "read_from_module_artifacts_when_available",
            "zero_live_api_calls": True,
            "counts": {
                "subjects": len(subjects),
                "prompts": len(prompts),
                "content_items": len(content_items),
                "validation_runs": len(validation_runs),
                "automation_jobs": len(automation_jobs),
                "video_items": len(video_items),
                "publishing_items": len(publishing_items),
                "analytics_items": len(analytics_items),
                "agent_personas": len(agent_personas),
            },
        }

        return DashboardSnapshot(
            project=project,
            subjects=subjects,
            prompts=prompts,
            content_items=content_items,
            validation_runs=validation_runs,
            automation_jobs=automation_jobs,
            video_items=video_items,
            publishing_items=publishing_items,
            analytics_items=analytics_items,
            agent_personas=agent_personas,
            system=system,
            advisories=advisories,
        )

    def project_summary(self) -> ProjectSummary:
        sections = sorted(path.name for path in self.config_root.iterdir() if path.is_dir()) if self.config_root.exists() else []
        return ProjectSummary(
            project=self.project,
            display_name=PROJECT_DISPLAY.get(self.project, self.project),
            prompt_name=PROJECT_PROMPT_DISPLAY.get(self.project, self.project),
            config_sections=sections,
        )

    def subject_assets(self) -> list[SubjectAsset]:
        subjects_dir = self.config_root / "subjects"
        knowledge_dir = self.data_root / "knowledge"
        names = set(EXPECTED_SUBJECTS)
        if subjects_dir.exists():
            names.update(path.stem for path in subjects_dir.glob("*.yaml") if not path.name.endswith(".overrides.yaml"))
        assets = []
        for subject in sorted(names):
            prefix = f"VENHO_HOTEL_{subject.upper()}_DNA"
            assets.append(
                SubjectAsset(
                    subject=subject,
                    has_config=(subjects_dir / f"{subject}.yaml").exists(),
                    has_overrides=(subjects_dir / f"{subject}.overrides.yaml").exists(),
                    has_dna_json=(knowledge_dir / f"{prefix}.json").exists(),
                    has_dna_md=(knowledge_dir / f"{prefix}.md").exists(),
                    has_compact=(knowledge_dir / f"{prefix}_COMPACT.md").exists(),
                    manifest=_rel(knowledge_dir / f"dna_manifest_{subject}.json", self.base_dir)
                    if (knowledge_dir / f"dna_manifest_{subject}.json").exists()
                    else None,
                )
            )
        return assets

    def prompt_items(self) -> list[dict[str, Any]]:
        manifest = _read_json(self.data_root / "prompts" / "prompt_manifest.json")
        return list(manifest.get("prompts", [])) if isinstance(manifest.get("prompts"), list) else []

    def content_items(self) -> list[dict[str, Any]]:
        manifest = _read_json(self.data_root / "content" / "content_manifest.json")
        return list(manifest.get("items", [])) if isinstance(manifest.get("items"), list) else []

    def validation_runs(self) -> list[dict[str, Any]]:
        manifest = _read_json(self.data_root / "validation" / "validation_manifest.json")
        runs = manifest.get("runs", [])
        if not isinstance(runs, list):
            return []
        normalized = []
        for run in runs[-30:]:
            if not isinstance(run, dict):
                continue
            item = dict(run)
            item["report_json"] = _rel(item.get("report_json"), self.base_dir)
            item["report_md"] = _rel(item.get("report_md"), self.base_dir)
            if item.get("validation_type") == "face":
                item["face_lock_gate"] = face_gate_status(item.get("overall_score"))
            normalized.append(item)
        return normalized

    def automation_jobs(self) -> list[dict[str, Any]]:
        state_dir = self.base_dir / "data" / "automation_runs" / "state"
        jobs = []
        for path in _latest_files(list(state_dir.glob("*.json")) if state_dir.exists() else [], 12):
            data = _read_json(path)
            if data:
                jobs.append(
                    {
                        "run_id": data.get("run_id", path.stem),
                        "workflow_id": data.get("workflow_id"),
                        "status": data.get("status"),
                        "started_at": data.get("started_at"),
                        "finished_at": data.get("finished_at"),
                        "step_count": len(data.get("steps", [])) if isinstance(data.get("steps"), list) else 0,
                        "manual_gate": data.get("manual_gate"),
                        "path": _rel(path, self.base_dir),
                    }
                )
        return jobs

    def video_items(self) -> list[dict[str, Any]]:
        manifest = _read_json(self.data_root / "video" / "video_manifest.json")
        items = manifest.get("items", [])
        if not isinstance(items, list):
            return []
        return [dict(item) for item in items if isinstance(item, dict)]

    def publishing_items(self) -> list[dict[str, Any]]:
        publishing_dir = self.data_root / "publishing"
        items = []
        for path in _latest_files(list(publishing_dir.rglob("*.json")) if publishing_dir.exists() else [], 20):
            data = _read_json(path)
            if not data:
                continue
            items.append(
                {
                    "id": data.get("package_id") or data.get("receipt_id") or path.stem,
                    "project": data.get("project", self.project),
                    "status": data.get("overall_status") or data.get("package_status") or data.get("status", "available"),
                    "platforms": data.get("platforms") or list(data.get("platform_results", {}).keys()),
                    "approval": data.get("approval", {}),
                    "path": _rel(path, self.base_dir),
                }
            )
        return items

    def analytics_items(self) -> list[dict[str, Any]]:
        analytics_dir = self.data_root / "analytics"
        items = []
        for path in _latest_files(list(analytics_dir.rglob("*.json")) if analytics_dir.exists() else [], 20):
            data = _read_json(path)
            if data:
                items.append(
                    {
                        "id": data.get("snapshot_id") or data.get("advisory_id") or data.get("alert_id") or path.stem,
                        "status": data.get("status") or data.get("performance_label") or data.get("severity", "available"),
                        "path": _rel(path, self.base_dir),
                    }
                )
        return items

    def agent_personas(self) -> list[dict[str, Any]]:
        agents_dir = self.config_root / "agents"
        personas = []
        for path in sorted(agents_dir.glob("*.yaml")) if agents_dir.exists() else []:
            if path.name == "agent_policy.yaml":
                continue
            data = _read_yaml(path)
            personas.append(
                {
                    "agent": path.stem,
                    "display_name": data.get("display_name", path.stem),
                    "allowed_modules": data.get("allowed_modules", []),
                    "path": _rel(path, self.base_dir),
                }
            )
        return personas


def build_dashboard_snapshot(base_dir: Path | str = Path("."), project: str = DEFAULT_PROJECT) -> DashboardSnapshot:
    return DashboardGateway(base_dir=base_dir, project=project).build_snapshot()
