from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from shared.logging import log
from shared.vision.client import VisionClient
from shared.vision.errors import RetryExhausted, SchemaValidationError, ProviderError
from shared.vision.image_loader import image_hash
from knowledge_studio.vision.schemas.base import ObservedFeature, BaseObservation
from knowledge_studio.vision.subject_registry import SubjectDef


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_path(
    obs_dir: Path,
    img_hash: str,
    schema_id: str,
    schema_version: str,
    prompt_version: str,
) -> Path:
    # schema_id included so different subjects sharing the same image never collide
    cache_key = f"{img_hash}_{schema_id}_{schema_version}_{prompt_version}"
    return obs_dir / f"{cache_key}.json"


def _load_cache(cache_file: Path, subject_def: SubjectDef) -> BaseObservation | None:
    if not cache_file.exists():
        return None
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        return subject_def.observation_cls(**data)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Single-image observe
# ---------------------------------------------------------------------------

def observe_image(
    image_path: Path,
    obs_dir: Path,
    client: VisionClient,
    schema_version: str,
    prompt_version: str,
    subject_def: SubjectDef,
    mode: Literal["A", "B"] = "B",
    max_attempts: int = 2,
    backoff_seconds: float = 2.0,
) -> BaseObservation:
    img_hash = image_hash(image_path)
    schema_id = getattr(subject_def, "schema_id", "universal")
    cache_file = _cache_path(obs_dir, img_hash, schema_id, schema_version, prompt_version)

    cached = _load_cache(cache_file, subject_def)
    if cached is not None:
        log(f"  [CACHE HIT] {image_path.name}")
        return cached

    log(f"  [OBSERVE]   {image_path.name}")
    system_prompt = subject_def.observe_prompt.read_text(encoding="utf-8")

    # Inject subject-specific aggregation keys so AI uses exactly these key names
    akeys = getattr(subject_def, "aggregation_keys", [])
    if akeys:
        lines = [
            "\n\nSUBJECT-SPECIFIC REQUIRED KEYS:",
            "You MUST report a value for EACH of the following keys in the 'features' array.",
            "Use 'not_visible' + confidence 0.0 only if the feature is truly not visible.",
            "Use EXACTLY these key names — do NOT invent other key names outside this list.",
            "",
        ]
        for akey in akeys:
            key_name = akey["key"] if isinstance(akey, dict) else akey
            atype = akey.get("type", "free") if isinstance(akey, dict) else "free"
            values = akey.get("values", []) if isinstance(akey, dict) else []
            if atype == "enum" and values:
                vals_str = ", ".join(str(v) for v in values)
                lines.append(f"- {key_name}  [enum — allowed values: {vals_str}]")
            else:
                lines.append(f"- {key_name}  [free text]")
        system_prompt = system_prompt + "\n" + "\n".join(lines)

    last_error: Exception = RuntimeError("no attempts made")
    for attempt in range(1, max_attempts + 1):
        try:
            raw = client.analyze_image(image_path, system_prompt)
            break
        except Exception as exc:
            last_error = exc
            log(f"  [WARN] attempt {attempt}/{max_attempts} failed: {exc}")
            if attempt < max_attempts:
                time.sleep(backoff_seconds)
    else:
        raise RetryExhausted(image_path.name, max_attempts, last_error)

    features = []
    for f in raw.get("features", []):
        try:
            features.append(ObservedFeature(**f))
        except Exception:
            pass

    obs = subject_def.observation_cls(
        mode=mode,
        image_hash=img_hash,
        image_file=image_path.name,
        subject=subject_def.name,
        schema_id=schema_id,
        schema_version=schema_version,
        prompt_version=prompt_version,
        provider=client.image_provider_name,
        model=client.image_model,
        observed_at=datetime.now().isoformat(),
        features=features,
        notable_features=raw.get("notable_features", []),
        uncertainty=raw.get("uncertainty", []),
        forbidden_hints=raw.get("forbidden_hints", []),
    )

    obs_dir.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(obs.model_dump_json(indent=2), encoding="utf-8")
    return obs


# ---------------------------------------------------------------------------
# Batch observe (with concurrency + isolation)
# ---------------------------------------------------------------------------

@dataclass
class ObserveReport:
    total: int
    processed: int = 0
    cache_hits: int = 0
    failed: list[str] = field(default_factory=list)
    output_dir: str = ""

    def print(self) -> None:
        log("-" * 40)
        log(f"Run Report")
        log(f"  Total images  : {self.total}")
        log(f"  Processed     : {self.processed}")
        log(f"  Cache hits    : {self.cache_hits}")
        log(f"  Failed        : {len(self.failed)}")
        if self.failed:
            for f in self.failed:
                log(f"    - {f}")
        if self.output_dir:
            log(f"  Output dir    : {self.output_dir}")
        log("-" * 40)


def observe_all(
    image_paths: list[Path],
    obs_dir: Path,
    client: VisionClient,
    schema_version: str,
    prompt_version: str,
    subject_def: SubjectDef,
    mode: Literal["A", "B"] = "B",
    concurrency: int = 4,
    max_attempts: int = 2,
    backoff_seconds: float = 2.0,
) -> tuple[list[BaseObservation], ObserveReport]:
    """Run Pass 1 on all images with concurrency and batch isolation.

    Returns (observations, report). One image failure does not kill the batch.
    """
    report = ObserveReport(total=len(image_paths), output_dir=str(obs_dir))
    observations: list[BaseObservation | None] = [None] * len(image_paths)

    schema_id = getattr(subject_def, "schema_id", "universal")

    def _worker(idx: int, path: Path) -> tuple[int, BaseObservation | None, bool, str | None]:
        """Returns (idx, obs_or_none, was_cache_hit, error_msg_or_none)."""
        img_hash_val = image_hash(path)
        cache_file = _cache_path(obs_dir, img_hash_val, schema_id, schema_version, prompt_version)
        if _load_cache(cache_file, subject_def) is not None:
            obs = _load_cache(cache_file, subject_def)
            return idx, obs, True, None
        try:
            obs = observe_image(
                path, obs_dir, client, schema_version, prompt_version, subject_def,
                mode=mode, max_attempts=max_attempts, backoff_seconds=backoff_seconds,
            )
            return idx, obs, False, None
        except Exception as exc:
            return idx, None, False, str(exc)

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(_worker, i, p): i for i, p in enumerate(image_paths)}
        for future in as_completed(futures):
            idx, obs, was_cache, error = future.result()
            if error:
                log(f"  [FAIL] {image_paths[idx].name}: {error}")
                report.failed.append(image_paths[idx].name)
            else:
                observations[idx] = obs
                report.processed += 1
                if was_cache:
                    report.cache_hits += 1

    result = [o for o in observations if o is not None]
    return result, report
