from __future__ import annotations

from pathlib import Path
from dataclasses import replace

import yaml

from shared.logging import log, init_log
from shared.vision.client import VisionClient
from shared.vision.image_loader import load_images
from knowledge_studio.vision.pass1_observe import observe_all
from knowledge_studio.vision.subject_resolver import resolve, SubjectDef

BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_PATH = BASE_DIR / "config" / "settings.yaml"

MODE_C_WARDROBE_VARIANTS = {
    "mint_green": {
        "display_label": "Nike Mint Green Running",
        "schema_subject": "outfit_e_sport",
        "family": "sport_active",
    },
    "nike_pink_running": {
        "display_label": "Nike Pink Running",
        "schema_subject": "outfit_e_sport",
        "family": "sport_active",
    },
}


def _load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def _make_client(cfg: dict, provider_override: str | None = None) -> VisionClient:
    image_provider = provider_override or cfg.get("ai", {}).get("image_extraction_provider", "openai")
    if image_provider == "mock":
        from shared.vision.client import MockVisionClient
        return MockVisionClient()
    return VisionClient(
        image_provider=image_provider,
        synthesis_provider=cfg.get("ai", {}).get("consolidation_provider", "claude"),
        image_model=cfg["models"]["openai"],
        synthesis_model=cfg["models"]["claude"],
        temperature=cfg.get("temperature", 0),
    )


def _log_path(base: Path, subject: str = "") -> Path:
    from datetime import datetime
    sub = f"/{subject}" if subject else ""
    log_dir = BASE_DIR / "data" / "observations" / subject if subject else BASE_DIR / "data" / "observations"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"pipeline-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"


# ---------------------------------------------------------------------------
# Mode A — single images to observation .md + .json
# ---------------------------------------------------------------------------

def run_mode_a(
    input_dir: Path,
    output_dir: Path | None = None,
    provider: str | None = None,
) -> list[dict[str, Path]]:
    """Mode A: each image → observation .md + .json in output_dir."""
    from knowledge_studio.vision.renderers.single_md import write_mode_a_output
    from knowledge_studio.vision.subject_resolver import _observe_prompt_path
    from knowledge_studio.vision.schemas.universal import UniversalObservation

    cfg = _load_config()
    log_path = _log_path(BASE_DIR)
    init_log(log_path)

    log("=" * 60)
    log("VENHO AI Studio — Mode A: Image Observation")
    log(f"Input   : {input_dir}")

    if output_dir is None:
        default = cfg.get("mode_a", {}).get("default_output", "data/projects/_inbox/output")
        output_dir = BASE_DIR / default
    log(f"Output  : {output_dir}")
    log("=" * 60)

    client = _make_client(cfg, provider)

    if not input_dir.is_absolute():
        input_dir = BASE_DIR / input_dir

    images = load_images(input_dir)
    if not images:
        raise FileNotFoundError(f"No images found in: {input_dir}")
    log(f"Found {len(images)} images\n")

    # Use universal subject def for Mode A
    from knowledge_studio.vision._subject_classes import get_observation_cls, get_dna_cls
    from dataclasses import dataclass

    class _UniversalSubjectDef:
        name = "universal"
        display_name = "Universal"
        schema_id = "universal"
        schema_version = cfg.get("schema_version", "1.0")
        observe_prompt = _observe_prompt_path("universal")
        observation_cls = UniversalObservation
        dna_cls = None
        aggregation_keys = []
        forbidden_defaults = []

    subject_def = _UniversalSubjectDef()

    obs_dir = BASE_DIR / "data" / "observations" / "universal"
    schema_version = cfg.get("schema_version", "1.0")
    prompt_version = cfg.get("prompt_version", "1.0")
    retry_cfg = cfg.get("retry", {})

    log("--- PASS 1: Observe ---")
    observations, report = observe_all(
        images, obs_dir, client, schema_version, prompt_version, subject_def,
        mode="A",
        concurrency=cfg.get("concurrency", 4),
        max_attempts=retry_cfg.get("max_attempts", 2),
        backoff_seconds=retry_cfg.get("backoff_seconds", 2),
    )
    log(f"  → {report.processed} processed, {report.cache_hits} cache hits, {len(report.failed)} failed\n")

    log("--- RENDER ---")
    results = []
    for obs in observations:
        paths = write_mode_a_output(obs, output_dir)
        log(f"  {obs.image_file} → {paths['md'].name}")
        results.append(paths)

    report.output_dir = str(output_dir)
    report.print()
    return results


# ---------------------------------------------------------------------------
# Mode B — multiple images of same subject → DNA
# ---------------------------------------------------------------------------

def run_mode_b(
    project: str,
    subject: str,
    input_dir: Path,
    dna_version: str = "1.0",
    provider: str | None = None,
    allow_universal_schema: bool = True,
) -> dict[str, Path]:
    """Mode B: multiple images → DNA .md + .json."""
    subject_def = resolve(project, subject, allow_universal_schema=allow_universal_schema)
    return _run_mode_b_with_subject_def(
        project=project,
        subject=subject,
        input_dir=input_dir,
        dna_version=dna_version,
        provider=provider,
        subject_def=subject_def,
    )


def run_mode_c(
    project: str,
    outfit_id: str,
    input_dir: Path,
    dna_version: str = "1.0",
    provider: str | None = None,
    schema_subject: str | None = None,
    display_label: str | None = None,
) -> dict[str, Path]:
    """Mode C: Linh An wardrobe variant → DNA, using a canonical schema subject.

    Mode C separates:
      - outfit_id: stable user-facing variant/artifact ID;
      - schema_subject: canonical schema used for observation/consolidation;
      - display_label: friendly label shown in logs/UI.

    Universal schema fallback is never allowed here.
    """
    if project != "linh_an":
        raise ValueError("Mode C currently supports project='linh_an' only.")

    variant = MODE_C_WARDROBE_VARIANTS.get(outfit_id)
    if variant is None:
        allowed = ", ".join(sorted(MODE_C_WARDROBE_VARIANTS))
        raise ValueError(f"Unknown Mode C outfit_id '{outfit_id}'. Allowed: {allowed}")

    effective_schema_subject = schema_subject or variant["schema_subject"]
    if effective_schema_subject != variant["schema_subject"]:
        raise ValueError(
            f"Mode C outfit_id '{outfit_id}' must use schema_subject "
            f"'{variant['schema_subject']}', got '{effective_schema_subject}'."
        )

    schema_def = resolve(project, effective_schema_subject, allow_universal_schema=False)
    subject_def = replace(
        schema_def,
        name=outfit_id,
        display_name=display_label or variant["display_label"],
        dna_filename=f"{project.upper()}_{outfit_id.upper()}_DNA",
    )

    return _run_mode_b_with_subject_def(
        project=project,
        subject=outfit_id,
        input_dir=input_dir,
        dna_version=dna_version,
        provider=provider,
        subject_def=subject_def,
        mode_label="Mode C: Linh An Wardrobe DNA",
        schema_subject=effective_schema_subject,
    )


def _run_mode_b_with_subject_def(
    project: str,
    subject: str,
    input_dir: Path,
    dna_version: str,
    provider: str | None,
    subject_def: SubjectDef,
    mode_label: str = "Mode B: DNA Builder",
    schema_subject: str | None = None,
) -> dict[str, Path]:
    """Shared implementation for Mode B and strict Mode C."""
    from knowledge_studio.vision.pass2_consolidate import consolidate
    from knowledge_studio.vision.renderers.dna_md import write_dna_output

    cfg = _load_config()

    obs_dir_key = f"data/projects/{project}/observations"
    obs_dir = BASE_DIR / obs_dir_key
    knowledge_dir = BASE_DIR / f"data/projects/{project}/knowledge"

    log_path = _log_path(BASE_DIR, subject)
    init_log(log_path)

    log("=" * 60)
    log(f"VENHO AI Studio — {mode_label}")
    log(f"Project : {project}")
    if schema_subject:
        log(f"Outfit  : {subject}")
        log(f"Schema subject: {schema_subject}")
    log(f"Subject : {subject_def.display_name}")
    log(f"Schema  : {subject_def.schema_source}")
    log(f"Input   : {input_dir}")
    log(f"DNA ver : {dna_version}")
    log("=" * 60)

    if not input_dir.is_absolute():
        input_dir = BASE_DIR / input_dir

    images = load_images(input_dir)
    if not images:
        raise FileNotFoundError(f"No images found in: {input_dir}")

    if len(images) < 2:
        log("⚠  WARNING: DNA needs multiple images of the same subject. Consider Mode A instead.")

    log(f"Found {len(images)} images\n")

    client = _make_client(cfg, provider)

    schema_version = cfg.get("schema_version", "1.0")
    prompt_version = cfg.get("prompt_version", "1.0")
    retry_cfg = cfg.get("retry", {})

    log("--- PASS 1: Observe ---")
    observations, report = observe_all(
        images, obs_dir, client, schema_version, prompt_version, subject_def,
        mode="B",
        concurrency=cfg.get("concurrency", 4),
        max_attempts=retry_cfg.get("max_attempts", 2),
        backoff_seconds=retry_cfg.get("backoff_seconds", 2),
    )
    log(f"  → {report.processed} processed, {report.cache_hits} cache hits, {len(report.failed)} failed\n")

    if not observations:
        raise RuntimeError("All images failed in Pass 1. Cannot build DNA.")

    # --- DNA Regeneration policy ---
    from knowledge_studio.vision.dna_manifest import (
        load_manifest, needs_regeneration, archive_dna, bump_version, save_manifest
    )
    source_hashes = [obs.image_hash for obs in observations]
    manifest = load_manifest(knowledge_dir, subject)

    if not needs_regeneration(manifest, source_hashes, schema_version, prompt_version):
        log("⚑  No image changes detected — DNA is up to date. Skipping regeneration.")
        # v2.4: overlay may have changed → still re-render (no vision calls, no version bump)
        from knowledge_studio.vision.overlay_merge import load_overlay, apply_overlay
        overlay = load_overlay(project, subject)
        if overlay:
            existing_json_path = knowledge_dir / f"{subject_def.dna_filename}.json"
            if existing_json_path.exists():
                import json as _json
                raw = _json.loads(existing_json_path.read_text(encoding="utf-8"))
                dna_from_json = subject_def.dna_cls.model_validate(raw)
                dna_merged = apply_overlay(dna_from_json, overlay)
                write_compact = cfg.get("output", {}).get("compact", False)
                paths = write_dna_output(dna_merged, knowledge_dir, subject_def.dna_filename, project, write_compact=write_compact)
                log("  [overlay] applied (render-only, no version bump)")
                log("=" * 60)
                log("COMPLETE (no change, overlay re-rendered)")
                log("=" * 60)
                report.print()
                return paths
        existing_md = knowledge_dir / f"{subject_def.dna_filename}.md"
        existing_json = knowledge_dir / f"{subject_def.dna_filename}.json"
        log("=" * 60)
        log("COMPLETE (no change)")
        log("=" * 60)
        report.print()
        return {"md": existing_md, "json": existing_json}

    if manifest is not None:
        old_version = manifest.get("current_version", dna_version)
        dna_version = bump_version(old_version)
        log(f"  Images changed — archiving v{old_version}, new version: v{dna_version}")
        archive_dna(knowledge_dir, subject_def.dna_filename, old_version)

    log("--- PASS 2: Consolidate ---")
    thresholds = {
        "consolidation_threshold": cfg.get("consolidation_threshold", 0.6),
        "consistency_threshold": cfg.get("consistency_threshold", 0.7),
        "weak_threshold": cfg.get("weak_threshold", 0.3),
    }
    dna = consolidate(
        observations=observations,
        client=client,
        schema_version=schema_version,
        prompt_version=prompt_version,
        dna_version=dna_version,
        subject_def=subject_def,
        project=project,
        thresholds=thresholds,
    )
    log(f"  → {len(dna.invariant)} invariant")
    log(f"  → {len(dna.variable)} variable")
    log(f"  → {len(dna.forbidden)} forbidden")
    log(f"  → {len(dna.evidence.weak_features)} weak features\n")

    # --- Overlay Merge (v2.4 §5.2) ---
    from knowledge_studio.vision.overlay_merge import load_overlay, apply_overlay
    overlay = load_overlay(project, subject)
    if overlay:
        dna = apply_overlay(dna, overlay)
        log(f"  [overlay] applied: {len([f for f in dna.forbidden if f.source == 'curated'])} curated forbidden, {len(dna.curator_notes)} curator notes")
    else:
        log("  [overlay] none (no overrides.yaml found)")

    log("--- RENDER ---")
    write_compact = cfg.get("output", {}).get("compact", False)
    paths = write_dna_output(dna, knowledge_dir, subject_def.dna_filename, project, write_compact=write_compact)
    log(f"  Markdown : {paths['md']}")
    log(f"  JSON     : {paths['json']}")
    if "compact" in paths:
        log(f"  Compact  : {paths['compact']}")

    save_manifest(knowledge_dir, subject, dna, overlay_applied=(overlay is not None))
    log(f"  Manifest : {knowledge_dir}/dna_manifest_{subject}.json")
    log("")

    log("=" * 60)
    log("COMPLETE")
    log("=" * 60)
    report.print()

    return paths


# ---------------------------------------------------------------------------
# --all: run Mode B for every subject that has a media folder under the project
# ---------------------------------------------------------------------------

def run_all(
    project: str = "venho_hotel",
    dna_version: str = "1.0",
    provider: str | None = None,
) -> dict[str, dict[str, Path]]:
    """Run Mode B DNA builder for every subject folder found under data/projects/<project>/media/.

    A subject folder is discovered if it exists AND contains at least one image file.
    Skips subjects with no images (logs a warning instead of raising).

    Returns: dict mapping subject name → paths dict (md, json, optional compact).
    """
    media_root = BASE_DIR / "data" / "projects" / project / "media"
    if not media_root.is_dir():
        raise FileNotFoundError(f"Media root not found: {media_root}")

    results: dict[str, dict[str, Path]] = {}

    subject_dirs = sorted([d for d in media_root.iterdir() if d.is_dir()])
    if not subject_dirs:
        log(f"⚠  No subject folders found under {media_root}")
        return results

    log("=" * 60)
    log(f"VENHO AI Studio — --all mode (project: {project})")
    log(f"Found {len(subject_dirs)} subject folder(s): {[d.name for d in subject_dirs]}")
    log("=" * 60)

    for subject_dir in subject_dirs:
        subject = subject_dir.name
        images = load_images(subject_dir)
        if not images:
            log(f"  [{subject}] SKIP — no images found in {subject_dir}")
            continue
        log(f"\n→ [{subject}] {len(images)} image(s)")
        try:
            paths = run_mode_b(
                project=project,
                subject=subject,
                input_dir=subject_dir,
                dna_version=dna_version,
                provider=provider,
            )
            results[subject] = paths
        except Exception as e:
            log(f"  [{subject}] ERROR: {e}")

    log("\n" + "=" * 60)
    log(f"--all complete: {len(results)}/{len(subject_dirs)} subjects built")
    log("=" * 60)
    return results


# ---------------------------------------------------------------------------
# Legacy entry point (backward compat with old CLI)
# ---------------------------------------------------------------------------

def run(
    subject: str,
    input_dir: Path,
    dna_version: str = "1.0",
    project: str = "venho_hotel",
) -> dict[str, Path]:
    return run_mode_b(project=project, subject=subject, input_dir=input_dir, dna_version=dna_version)
