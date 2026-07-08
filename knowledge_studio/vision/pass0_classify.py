from __future__ import annotations

"""Pass 0 — Auto Classify images by subject.

Optional step, enabled by --classify flag.
Groups a mixed folder of images into subject buckets.
"""

from pathlib import Path
from datetime import datetime, timezone

import yaml

from shared.logging import log
from shared.vision.client import VisionClient
from shared.vision.image_loader import load_images

CLASSIFY_PROMPT_PATH = Path(__file__).parent / "prompts" / "classify.md"

KNOWN_SUBJECTS = ["room", "lobby", "facade", "westlake", "linh_an", "general"]


def classify_image(image_path: Path, client: VisionClient) -> str:
    """Classify a single image into a subject category. Returns subject string."""
    prompt = CLASSIFY_PROMPT_PATH.read_text(encoding="utf-8")
    try:
        raw = client.analyze_image(image_path, prompt)
        subject = raw.get("subject", "general")
        confidence = raw.get("confidence", 0.0)
        if subject not in KNOWN_SUBJECTS:
            subject = "general"
        log(f"  [{subject.upper():12s} {confidence:.2f}] {image_path.name}")
        return subject
    except Exception as exc:
        log(f"  [ERROR classify] {image_path.name}: {exc}")
        return "general"


def classify_folder(
    input_dir: Path,
    client: VisionClient,
    concurrency: int = 4,
) -> dict[str, list[Path]]:
    """Classify all images in a folder. Returns {subject: [paths]}."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    images = load_images(input_dir)
    if not images:
        log(f"No images found in {input_dir}")
        return {}

    log(f"Pass 0 — classifying {len(images)} images…")
    groups: dict[str, list[Path]] = {s: [] for s in KNOWN_SUBJECTS}

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(classify_image, img, client): img for img in images}
        for future in as_completed(futures):
            img = futures[future]
            subject = future.result()
            groups.setdefault(subject, []).append(img)

    log(f"Classification summary:")
    for subject, paths in groups.items():
        if paths:
            log(f"  {subject}: {len(paths)} image(s)")

    return {k: v for k, v in groups.items() if v}


def write_classification_review(
    groups: dict[str, list[Path]],
    output_path: Path,
    input_dir: Path | None = None,
) -> Path:
    """Write a human-review manifest for Pass 0 groups.

    This file is intentionally not an execution input for Mode B. It is a review
    artifact so a human can confirm subjects before moving images into subject
    folders.
    """
    review = {
        "status": "pending_human_review",
        "approved_for_mode_b": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_dir": str(input_dir) if input_dir else "",
        "instructions": [
            "Review each suggested subject group.",
            "Move or copy approved images into data/projects/<project>/media/<subject>/.",
            "Only run Mode B after each folder contains exactly one confirmed subject.",
        ],
        "groups": {
            subject: [str(path) for path in paths]
            for subject, paths in sorted(groups.items())
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.dump(review, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    log(f"Classification review saved: {output_path}")
    return output_path
