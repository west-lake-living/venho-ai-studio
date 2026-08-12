from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Optional

from .config import ComfyUIConfig
from .models import ActionCompositeJob, CompositeResult
from .pipeline import ActionCompositePipeline
from .providers import IdentityRestorer
from .service import ActionCompositeService, JobEnvelope


class ProductionRunner:
    """Wires the application service to the local Action Composite pipeline."""

    def __init__(self, *, service: ActionCompositeService, pipeline: Optional[ActionCompositePipeline] = None,
                 config: Optional[ComfyUIConfig] = None) -> None:
        self.service = service
        self.pipeline = pipeline or ActionCompositePipeline()
        self.config = config or ComfyUIConfig.from_env()

    def health_check(self, restorer: IdentityRestorer) -> bool:
        checker = getattr(restorer, "health_check", None)
        if checker is None:
            raise RuntimeError("Configured identity restorer does not expose health_check")
        return bool(checker())

    def submit_and_run(self, job: ActionCompositeJob, restorer: IdentityRestorer, *, output_dir: str | Path,
                       identity_score: Optional[float] = None, geometry_score: Optional[float] = None,
                       request_payload: bytes = b"", health_gate: bool = True) -> JobEnvelope:
        if health_gate and not self.health_check(restorer):
            raise RuntimeError("ComfyUI identity restorer health check failed")
        envelope = self.service.submit(job, request_payload=request_payload)
        if envelope.status.value == "COMPLETED":
            return envelope

        restorer_config = self._restorer_config()

        def execute(current: ActionCompositeJob) -> CompositeResult:
            result = self.pipeline.run(current, restorer, output_dir=output_dir,
                                       identity_score=identity_score, geometry_score=geometry_score,
                                       restorer_config=restorer_config)
            self._verify_artifacts(result.output_path)
            return result

        return self.service.run(job.job_id, execute)

    def _restorer_config(self) -> dict[str, Any]:
        """Hand the restorer everything it needs to reach ComfyUI.

        The workflow document is only loaded when one is configured, so the
        offline pipeline and its fake restorers keep working with no ComfyUI
        installation present.
        """
        config: dict[str, Any] = {"workflow_version": self.config.workflow_version,
                                  "timeout_seconds": self.config.timeout_seconds,
                                  "node_bindings": self.config.node_bindings}
        if self.config.workflow_path:
            config["workflow"] = self.config.load_workflow()
        return config

    @staticmethod
    def _verify_artifacts(output_path: str) -> None:
        image_path = Path(output_path)
        manifest_path = image_path.parent / "manifest.json"
        if not image_path.is_file() or image_path.stat().st_size == 0:
            raise RuntimeError("Production artifact image.png is missing or empty")
        if not manifest_path.is_file():
            raise RuntimeError("Production artifact manifest.json is missing")
        try:
            manifest: Any = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError("Production manifest is not valid JSON") from exc
        if not isinstance(manifest, dict) or not manifest.get("artifacts"):
            raise RuntimeError("Production manifest has no artifacts")
