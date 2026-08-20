from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from ...application.ports.workflow_repository import WorkflowDescriptor
from ...domain.errors import RestorationError


@dataclass
class FileWorkflowRepository:
    """Reads a workflow JSON from disk and verifies its sha256 against the pin
    in config/projects/venho_hotel/identity_restoration/workflow_pins.yaml
    (GW-D6: workflow JSON is source code; a changed workflow with an
    unchanged hash pin is a hard fail, not a warning)."""

    workflow_root: Path
    pins_path: Path

    def load(self, workflow_id: str) -> tuple[dict, WorkflowDescriptor]:
        pins = yaml.safe_load(self.pins_path.read_text(encoding="utf-8")) or {}
        entry = (pins.get("workflows") or {}).get(workflow_id)
        if entry is None:
            raise RestorationError("ERR_GW_WORKFLOW_INVALID", f"no pin for workflowId {workflow_id!r}",
                                   retryable=False)
        path = self._resolve_path(workflow_id, entry)
        data = path.read_bytes()
        actual_sha256 = hashlib.sha256(data).hexdigest()
        pinned_sha256 = entry.get("sha256", "")
        if not pinned_sha256 or pinned_sha256.startswith("<"):
            raise RestorationError("ERR_GW_WORKFLOW_INVALID",
                                   f"workflowId {workflow_id!r} has no sha256 pinned yet", retryable=False)
        if actual_sha256 != pinned_sha256:
            raise RestorationError(
                "ERR_GW_WORKFLOW_INVALID",
                f"workflow {workflow_id!r} sha256 mismatch: file={actual_sha256} pin={pinned_sha256}",
                retryable=False,
            )
        workflow = json.loads(data)
        models = entry.get("models")
        model_ids = tuple(models.values()) if isinstance(models, dict) else tuple(models or ())
        descriptor = WorkflowDescriptor(
            workflow_id=workflow_id, filename=path.name, sha256=actual_sha256,
            models=model_ids, min_vram_mb=int(entry.get("min_vram_mb", 0)),
        )
        return workflow, descriptor

    def _resolve_path(self, workflow_id: str, entry: dict) -> Path:
        explicit = entry.get("path")
        if explicit:
            return Path(explicit)
        filename = entry.get("filename", f"{workflow_id}.api.json")
        return self.workflow_root / filename
