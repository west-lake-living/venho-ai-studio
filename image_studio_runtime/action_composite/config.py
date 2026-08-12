from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from pydantic import BaseModel, Field

from .providers import DEFAULT_NODE_BINDINGS

#: Repository root, so a relative workflow path resolves the same way no matter
#: which directory the CLI, worker or test runner was started from.
BASE_DIR = Path(__file__).resolve().parents[2]


class ComfyUIConfig(BaseModel):
    endpoint: str = "http://127.0.0.1:8188"
    workflow_version: str = "face_restore_v1"
    workflow_path: Optional[str] = None
    timeout_seconds: float = Field(default=120.0, gt=0)
    client_id: str = "venho-action-composite"
    node_bindings: Dict[str, str] = Field(default_factory=lambda: dict(DEFAULT_NODE_BINDINGS))

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "ComfyUIConfig":
        values = env if env is not None else os.environ
        return cls(endpoint=values.get("VENHO_COMFYUI_ENDPOINT", cls.model_fields["endpoint"].default),
                   workflow_version=values.get("VENHO_COMFYUI_WORKFLOW_VERSION",
                                               cls.model_fields["workflow_version"].default),
                   workflow_path=values.get("VENHO_COMFYUI_WORKFLOW_PATH"),
                   timeout_seconds=_float_env(values, "VENHO_COMFYUI_TIMEOUT_SECONDS",
                                              cls.model_fields["timeout_seconds"].default),
                   client_id=values.get("VENHO_COMFYUI_CLIENT_ID", cls.model_fields["client_id"].default),
                   node_bindings=_bindings_env(values))

    def load_workflow(self, base_dir: str | Path | None = None) -> dict[str, Any]:
        if not self.workflow_path:
            raise ValueError("VENHO_COMFYUI_WORKFLOW_PATH is required for a live restoration")
        path = Path(self.workflow_path)
        if not path.is_absolute():
            path = Path(base_dir if base_dir is not None else BASE_DIR) / path
        if not path.is_file():
            raise FileNotFoundError(f"ComfyUI workflow not found: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not payload:
            raise ValueError(f"ComfyUI workflow must be a non-empty JSON object: {path}")
        return payload


def _float_env(values: Mapping[str, str], name: str, default: float) -> float:
    raw = values.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw!r}") from exc


def _bindings_env(values: Mapping[str, str]) -> Dict[str, str]:
    raw = values.get("VENHO_COMFYUI_NODE_BINDINGS")
    if not raw:
        return dict(DEFAULT_NODE_BINDINGS)
    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        raise ValueError("VENHO_COMFYUI_NODE_BINDINGS must be a JSON object") from exc
    if not isinstance(parsed, dict):
        raise ValueError("VENHO_COMFYUI_NODE_BINDINGS must be a JSON object")
    return {str(key): str(value) for key, value in parsed.items()}
