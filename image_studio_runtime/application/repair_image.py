from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

from image_studio_runtime.adapters.mock_image_provider import MockImageProvider
from image_studio_runtime.application.generate_image import _is_transient_provider_error, _provider_model
from image_studio_runtime.domain.image_run import ImageRun, enforce_paid_attempt_policy
from image_studio_runtime.storage.run_store import RunStore


def build_repair_prompt(original_prompt: str, issue: str) -> str:
    if not issue.strip():
        raise ValueError("repair issue is required")
    return f"{original_prompt.strip()}\nTargeted repair: {issue.strip()}"


def repair_image_run(
    original_manifest: dict,
    *,
    issue: str,
    provider: MockImageProvider | None = None,
    data_root: Path = Path("data/projects"),
    existing_runs: list[ImageRun] | None = None,
    paid: bool = True,
) -> Path:
    if paid:
        enforce_paid_attempt_policy(existing_runs or [], operation="repair")
    selected_provider = provider or MockImageProvider()
    final_prompt = build_repair_prompt(original_manifest["final_prompt"], issue)
    run_id = str(uuid.uuid4())
    try:
        image_bytes = selected_provider.generate(final_prompt, size=original_manifest["size"], quality=original_manifest["quality"])
    except Exception as exc:
        if _is_transient_provider_error(exc):
            raise RuntimeError("Transient provider failure; backoff without creating a new variant") from exc
        raise
    manifest = {
        **original_manifest,
        "run_id": run_id,
        "operation": "edit",
        "model": original_manifest.get("model", _provider_model(selected_provider)),
        "final_prompt": final_prompt,
        "prompt_hash": "sha256:" + hashlib.sha256(final_prompt.encode("utf-8")).hexdigest(),
        "repair_of_run_id": original_manifest["run_id"],
        "repair_issue": issue,
        "paid": paid,
        "attempt_index": 2,
        "validation_run_ids": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return RunStore(data_root=data_root).create_run(original_manifest["content_package_id"], run_id, image_bytes, manifest)
