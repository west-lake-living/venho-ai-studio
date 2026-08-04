from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

from agent_studio.growth.scenario_registry import ScenarioRegistry
from image_studio_runtime.adapters.m02_prompt_bridge import build_final_prompt
from image_studio_runtime.adapters.mock_image_provider import ImageProviderTransientError
from image_studio_runtime.adapters.mock_image_provider import MockImageProvider
from image_studio_runtime.domain.image_run import ImageRun, enforce_paid_attempt_policy
from image_studio_runtime.storage.run_store import RunStore


def _provider_model(provider: object) -> str:
    return str(getattr(provider, "model", provider.__class__.__name__))


def _is_transient_provider_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    return status_code == 429 or (isinstance(status_code, int) and 500 <= status_code <= 599)


def generate_image_run(
    prompt_contract: dict,
    *,
    content_package_id: str,
    provider: MockImageProvider | None = None,
    data_root: Path = Path("data/projects"),
    paid: bool = False,
    existing_runs: list[ImageRun] | None = None,
    reference_images: list[bytes] | None = None,
) -> Path:
    if paid:
        enforce_paid_attempt_policy(existing_runs or [], operation="generate")
    final_prompt = build_final_prompt(prompt_contract)
    run_id = str(uuid.uuid4())
    selected_provider = provider or MockImageProvider()
    generate_kwargs: dict = {"size": prompt_contract.get("size", "1024x1280"), "quality": prompt_contract.get("quality", "medium")}
    if reference_images:
        generate_kwargs["reference_images"] = reference_images
    try:
        image_bytes = selected_provider.generate(final_prompt, **generate_kwargs)
    except Exception as exc:
        if _is_transient_provider_error(exc):
            raise RuntimeError("Transient provider failure; backoff without creating a new variant") from exc
        raise
    scenario = ScenarioRegistry.from_file().resolve(prompt_contract["scenario_key"])
    manifest = {
        "schema_version": "2.2",
        "run_id": run_id,
        "content_package_id": content_package_id,
        "creative_brief_id": prompt_contract["creative_brief_id"],
        "model": prompt_contract.get("model", _provider_model(selected_provider)),
        "operation": "generate",
        "quality": prompt_contract.get("quality", "medium"),
        "size": prompt_contract.get("size", "1024x1280"),
        "prompt_contract_version": prompt_contract.get("schema_version", "1.0"),
        "base_prompt": prompt_contract["base_prompt"],
        "override_patch": prompt_contract.get("override_patch", {}),
        "final_prompt": final_prompt,
        "prompt_hash": "sha256:" + hashlib.sha256(final_prompt.encode("utf-8")).hexdigest(),
        "reference_asset_ids": prompt_contract.get("reference_asset_ids", list(scenario.reference_asset_ids)),
        "reference_mode": prompt_contract.get("reference_mode", scenario.reference_mode),
        "dna_subject": prompt_contract.get("dna_subject", scenario.dna_subject),
        "dna_version": prompt_contract.get("dna_version", scenario.dna_version),
        "scenario_key": scenario.scenario_key,
        "required_entities": list(scenario.required_entities),
        "forbidden_entities": list(scenario.forbidden_entities),
        "paid": paid,
        "attempt_index": 1,
        "estimated_cost_minor": 0,
        "actual_cost_minor": None,
        "validation_run_ids": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return RunStore(data_root=data_root).create_run(content_package_id, run_id, image_bytes, manifest)
