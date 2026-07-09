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
OPERATING_STAGES = (
    "Observe",
    "DNA",
    "Prompt",
    "Validate",
    "Automation",
    "Video",
    "Publishing",
    "Analytics",
)


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
    operating_center: dict[str, Any]
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
        operating_center = self.operating_center_snapshot(
            advisories=advisories,
            subjects=subjects,
            prompts=prompts,
            content_items=content_items,
            validation_runs=validation_runs,
            automation_jobs=automation_jobs,
            video_items=video_items,
            publishing_items=publishing_items,
            analytics_items=analytics_items,
            agent_personas=agent_personas,
        )

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
            operating_center=operating_center,
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

    def operating_center_snapshot(
        self,
        *,
        advisories: list[Advisory],
        subjects: list[SubjectAsset],
        prompts: list[dict[str, Any]],
        content_items: list[dict[str, Any]],
        validation_runs: list[dict[str, Any]],
        automation_jobs: list[dict[str, Any]],
        video_items: list[dict[str, Any]],
        publishing_items: list[dict[str, Any]],
        analytics_items: list[dict[str, Any]],
        agent_personas: list[dict[str, Any]],
    ) -> dict[str, Any]:
        override = _read_json(self.base_dir / "artifacts" / "m10" / "home_snapshot.json")
        if override:
            return override

        failed_validations = [
            item
            for item in validation_runs
            if str(item.get("verdict") or item.get("status") or "").lower()
            in {"fail", "failed", "reject", "rejected", "regenerate"}
        ]
        review_validations = [
            item
            for item in validation_runs
            if str(item.get("verdict") or item.get("status") or "").lower()
            in {"conditional", "review", "needs_review", "warning"}
        ]
        active_jobs = [
            item
            for item in automation_jobs
            if str(item.get("status") or "").lower() in {"running", "pending", "waiting", "queued"}
        ]
        waiting_publish = [
            item
            for item in publishing_items
            if str(item.get("status") or "").lower() in {"waiting_approval", "pending", "ready", "draft"}
        ]

        tasks = self._today_tasks(
            failed_validations=failed_validations,
            review_validations=review_validations,
            waiting_publish=waiting_publish,
            prompts=prompts,
            analytics_items=analytics_items,
        )
        health = self._system_health(
            subjects=subjects,
            prompts=prompts,
            validation_runs=validation_runs,
            automation_jobs=automation_jobs,
            publishing_items=publishing_items,
            analytics_items=analytics_items,
        )
        worst_health = self._worst_status([item["status"] for item in health])
        health_warning_count = sum(
            1
            for item in health
            if self._worst_status([item["status"]]) in {"Warning", "Critical Failure", "Critical"}
        )
        publishing_status = "1 Post Ready" if waiting_publish else ("Ready" if publishing_items else "No Items")
        completed_tasks = sum(1 for task in tasks if task.get("status") == "Completed")

        return {
            "header": {
                "title": "VENHO AI STUDIO",
                "subtitle": "Operating Center",
                "project_scope": PROJECT_DISPLAY.get(self.project, self.project),
                "project_status": "ACTIVE",
                "last_sync": self._last_sync(automation_jobs, validation_runs),
                "mode": "Read-only",
                "build": "v2.0",
            },
            "current_focus": self._current_focus(tasks, automation_jobs),
            "summary_cards": [
                {"label": "Today's Tasks", "value": f"{len(tasks) - completed_tasks} Pending Tasks", "status": "Active"},
                {"label": "System Security", "value": f"{health_warning_count} Warnings Detected", "status": worst_health},
                {"label": "Automation Engine", "value": f"{len(active_jobs)} Running Jobs", "status": "Active" if active_jobs else "Ready"},
                {"label": "Publishing Queue", "value": publishing_status, "status": "Warning" if waiting_publish else ("Ready" if publishing_items else "Missing")},
            ],
            "today_progress": {"completed": completed_tasks, "total": len(tasks)},
            "today_tasks": tasks,
            "quick_actions": self._quick_actions(),
            "system_health": health,
            "pipeline": self._pipeline(
                subjects=subjects,
                prompts=prompts,
                content_items=content_items,
                validation_runs=validation_runs,
                automation_jobs=automation_jobs,
                video_items=video_items,
                publishing_items=publishing_items,
                analytics_items=analytics_items,
                failed_validations=failed_validations,
                review_validations=review_validations,
                waiting_publish=waiting_publish,
            ),
            "alerts": self._alerts(advisories, failed_validations, waiting_publish),
            "recent_activity": self._recent_activity(automation_jobs, validation_runs, content_items),
            "agents": self._agent_cards(agent_personas, health),
        }

    def _current_focus(
        self,
        tasks: list[dict[str, str]],
        automation_jobs: list[dict[str, Any]],
    ) -> dict[str, str | int | None]:
        running = [
            item
            for item in automation_jobs
            if str(item.get("status") or "").lower() in {"running", "pending", "waiting", "queued"}
        ]
        if running:
            job = running[0]
            return {
                "title": f"Continue {job.get('workflow_id') or 'automation workflow'}",
                "progress_label": f"Step {job.get('step_count') or 1} / {max(int(job.get('step_count') or 1), 1)}",
                "status": "In Progress",
                "action_label": "Continue",
                "empty": False,
            }
        actionable = [task for task in tasks if task.get("status") != "Completed"]
        if actionable:
            task = actionable[0]
            return {
                "title": task["task"],
                "progress_label": "Step 1 / 8",
                "status": "Needs Attention" if task["priority"] == "High" else "In Progress",
                "action_label": task.get("action_label", "Continue"),
                "empty": False,
            }
        return {
            "title": "No active focus.",
            "progress_label": None,
            "status": "Ready",
            "action_label": "Choose Today's Focus",
            "empty": True,
        }

    def _today_tasks(
        self,
        *,
        failed_validations: list[dict[str, Any]],
        review_validations: list[dict[str, Any]],
        waiting_publish: list[dict[str, Any]],
        prompts: list[dict[str, Any]],
        analytics_items: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        tasks: list[dict[str, str]] = []
        if failed_validations:
            tasks.append({"task": "Review failed validations", "priority": "High", "source": "Validator", "action_label": "Review", "status": "Pending"})
        if review_validations:
            tasks.append({"task": "Review conditional validation results", "priority": "Medium", "source": "Validator", "action_label": "Open", "status": "Pending"})
        if waiting_publish:
            tasks.append({"task": "Approve publishing queue", "priority": "Medium", "source": "Publishing", "action_label": "Approve", "status": "Pending"})
        if not prompts:
            tasks.append({"task": "Generate next room prompt", "priority": "Medium", "source": "Workbench", "action_label": "Generate", "status": "Pending"})
        if not analytics_items:
            tasks.append({"task": "Review analytics snapshot", "priority": "High", "source": "Insights", "action_label": "Open", "status": "Pending"})
        if not tasks:
            tasks.append({"task": "Review recent activity", "priority": "Low", "source": "Home", "action_label": "Open", "status": "Pending"})
        tasks.append({"task": "Backup knowledge snapshot", "priority": "Completed", "source": "System", "action_label": "Done", "status": "Completed"})
        return tasks[:5]

    def _quick_actions(self) -> list[dict[str, str]]:
        return [
            {"label": "+ Build DNA", "target": "Workbench"},
            {"label": "+ Generate Prompt", "target": "Workbench"},
            {"label": "+ Validate", "target": "Workbench"},
            {"label": "+ Prepare Publish", "target": "Publish"},
            {"label": "+ Create Video", "target": "Workbench"},
            {"label": "+ Run Automation", "target": "Workbench"},
        ]

    def _system_health(
        self,
        *,
        subjects: list[SubjectAsset],
        prompts: list[dict[str, Any]],
        validation_runs: list[dict[str, Any]],
        automation_jobs: list[dict[str, Any]],
        publishing_items: list[dict[str, Any]],
        analytics_items: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        missing_dna = any(not item.has_dna_json for item in subjects)
        failed_validation = any(
            str(item.get("verdict") or item.get("status") or "").lower()
            in {"fail", "failed", "reject", "rejected", "regenerate"}
            for item in validation_runs
        )
        failed_job = any(str(item.get("status") or "").lower() in {"failed", "error"} for item in automation_jobs)

        return [
            {"area": "Knowledge", "status": "Warning" if missing_dna else "Healthy"},
            {"area": "Prompt", "status": "Healthy" if prompts else "Missing"},
            {"area": "Validator", "status": "Critical Failure" if failed_validation else ("Healthy" if validation_runs else "Missing")},
            {"area": "Automation", "status": "Critical Failure" if failed_job else ("Healthy" if automation_jobs else "Missing")},
            {"area": "Publishing", "status": "Healthy" if publishing_items else "Warning"},
            {"area": "Analytics", "status": "Healthy" if analytics_items else "Missing"},
        ]

    def _pipeline(
        self,
        *,
        subjects: list[SubjectAsset],
        prompts: list[dict[str, Any]],
        content_items: list[dict[str, Any]],
        validation_runs: list[dict[str, Any]],
        automation_jobs: list[dict[str, Any]],
        video_items: list[dict[str, Any]],
        publishing_items: list[dict[str, Any]],
        analytics_items: list[dict[str, Any]],
        failed_validations: list[dict[str, Any]],
        review_validations: list[dict[str, Any]],
        waiting_publish: list[dict[str, Any]],
    ) -> list[dict[str, str | int]]:
        missing_dna = sum(1 for item in subjects if not item.has_dna_json)
        failed_jobs = sum(1 for item in automation_jobs if str(item.get("status") or "").lower() in {"failed", "error"})
        return [
            {"stage": "Observe", "status": "Ready", "ready": len(subjects), "need_review": 0, "failed": 0, "action": "Open Workbench"},
            {
                "stage": "DNA",
                "status": "Need Review" if missing_dna else "Ready",
                "ready": max(len(subjects) - missing_dna, 0),
                "need_review": missing_dna,
                "failed": 0,
                "action": "Build DNA" if missing_dna else "Browse Project",
            },
            {"stage": "Prompt", "status": "Ready" if prompts else "Need Review", "ready": len(prompts), "need_review": 0 if prompts else 1, "failed": 0, "action": "Generate Prompt"},
            {
                "stage": "Validate",
                "status": "Failed" if failed_validations else ("Need Review" if review_validations else "Ready"),
                "ready": len(validation_runs),
                "need_review": len(review_validations),
                "failed": len(failed_validations),
                "action": "Review Failed" if failed_validations else "Open Validator",
            },
            {"stage": "Automation", "status": "Failed" if failed_jobs else "Ready", "ready": len(automation_jobs), "need_review": 0, "failed": failed_jobs, "action": "Run Automation"},
            {"stage": "Video", "status": "Ready" if video_items else "Need Review", "ready": len(video_items), "need_review": 0 if video_items else 1, "failed": 0, "action": "Create Video"},
            {
                "stage": "Publishing",
                "status": "Need Review" if waiting_publish else ("Ready" if publishing_items else "Need Review"),
                "ready": len(publishing_items),
                "need_review": len(waiting_publish) if waiting_publish else (0 if publishing_items else 1),
                "failed": 0,
                "action": "Approve Queue",
            },
            {"stage": "Analytics", "status": "Ready" if analytics_items else "Need Review", "ready": len(analytics_items), "need_review": 0 if analytics_items else 1, "failed": 0, "action": "Review Snapshot"},
        ]

    def _alerts(
        self,
        advisories: list[Advisory],
        failed_validations: list[dict[str, Any]],
        waiting_publish: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        alerts = [
            {"status": "Warning", "message": advisory.message}
            for advisory in advisories
            if advisory.status in {"degraded", "advisory"}
        ]
        if failed_validations:
            alerts.insert(0, {"status": "Critical", "message": f"{len(failed_validations)} validation failure(s) need review."})
        if waiting_publish:
            alerts.insert(0, {"status": "Warning", "message": "Publishing queue waiting approval."})
        return alerts[:5]

    def _recent_activity(
        self,
        automation_jobs: list[dict[str, Any]],
        validation_runs: list[dict[str, Any]],
        content_items: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        activity: list[dict[str, str]] = []
        for item in automation_jobs[:4]:
            activity.append(
                {
                    "time": str(item.get("finished_at") or item.get("started_at") or "Recent"),
                    "event": f"Automation {item.get('status', 'updated')}",
                    "detail": str(item.get("workflow_id") or item.get("run_id") or ""),
                }
            )
        for item in validation_runs[-2:]:
            activity.append(
                {
                    "time": str(item.get("created_at") or item.get("finished_at") or "Recent"),
                    "event": "Validator completed",
                    "detail": str(item.get("subject") or item.get("validation_type") or ""),
                }
            )
        if content_items:
            activity.append({"time": "Recent", "event": "Content draft available", "detail": str(content_items[-1].get("id") or "")})
        return activity[:6]

    def _agent_cards(self, agent_personas: list[dict[str, Any]], health: list[dict[str, str]]) -> list[dict[str, str]]:
        health_map = {item["area"]: item["status"] for item in health}
        cards = []
        for persona in agent_personas:
            name = str(persona.get("display_name") or persona.get("agent"))
            modules = " ".join(str(module) for module in persona.get("allowed_modules", []))
            if "M07" in modules:
                status = "Waiting Approval" if health_map.get("Publishing") != "Healthy" else "Ready"
            elif "M03" in modules:
                status = health_map.get("Validator", "Ready")
            elif "M01" in modules:
                status = health_map.get("Knowledge", "Ready")
            else:
                status = "Ready"
            cards.append({"agent": name, "status": status})
        return cards

    def _last_sync(
        self,
        automation_jobs: list[dict[str, Any]],
        validation_runs: list[dict[str, Any]],
    ) -> str:
        candidates = []
        for item in automation_jobs:
            candidates.extend([item.get("finished_at"), item.get("started_at")])
        for item in validation_runs:
            candidates.extend([item.get("created_at"), item.get("finished_at")])
        values = sorted(str(value) for value in candidates if value)
        if not values:
            return "No sync yet"
        latest = values[-1]
        if "T" in latest:
            return latest.split("T", 1)[1][:5]
        parts = latest.split()
        return parts[-1][:5] if parts else latest[:5]

    def _worst_status(self, statuses: list[str]) -> str:
        order = {"Critical Failure": 4, "Critical": 4, "Warning": 3, "Missing": 2, "Active": 1, "Healthy": 0, "Ready": 0}
        if not statuses:
            return "Missing"
        return max(statuses, key=lambda status: order.get(status, 0))


def build_dashboard_snapshot(base_dir: Path | str = Path("."), project: str = DEFAULT_PROJECT) -> DashboardSnapshot:
    return DashboardGateway(base_dir=base_dir, project=project).build_snapshot()
