from __future__ import annotations

"""Harry's image choice for a queued draft: pick option A/B/C, or upload his
own photo (2026-10-21).

Only while the draft is PENDING_APPROVAL: the approval snapshot freezes
`package_snapshot.asset_version_ids`, so changing the image after Duyệt
would either dispatch an image nobody approved or fail the exact-version
check. Facebook and Instagram drafts of one slot share one image, so a
choice applies to every pending row of that slot and topic.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from growth_orchestrator.application.image_options import option as image_option_entry
from growth_orchestrator.application.image_options import to_upload_jpeg
from publishing_gateway.image_constraints import aspect_ratio_rejection, normalize_for_instagram
from publishing_gateway.publication_registry import PublicationRegistry
from shared.http import urllib_post

PENDING_STATUS = "PENDING_APPROVAL"


def _group(registry: PublicationRegistry, publication_id: str) -> list[dict[str, Any]]:
    rows = registry.load()["publications"]
    target = next((r for r in rows if r.get("publication_id") == publication_id), None)
    if target is None:
        raise KeyError(f"Unknown publication_id: {publication_id}")
    if target.get("status") != PENDING_STATUS:
        raise ValueError(
            f"{publication_id} is {target.get('status')}; the image can only change before Duyệt (PENDING_APPROVAL)"
        )
    if not target.get("slot_id"):
        return [target]
    return [
        r for r in rows
        if r.get("slot_id") == target["slot_id"] and r.get("topic") == target.get("topic") and r.get("status") == PENDING_STATUS
    ]


def _apply(registry: PublicationRegistry, rows: list[dict[str, Any]], chosen: dict[str, Any], *, options: list[dict[str, Any]], by: str) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    updated = []
    for row in rows:
        content = dict(row.get("content") or {})
        content.update(
            image_options=options,
            image_option_selected=chosen["id"],
            image_public_url=chosen["url"],
            image_is_fallback=chosen["kind"] == "fallback",
            image_fallback_reason=content.get("image_fallback_reason") if chosen["kind"] == "fallback" else None,
            image_selected_by=by,
            image_selected_at=now,
        )
        snapshot = dict(row.get("package_snapshot") or {})
        if snapshot:
            snapshot["asset_version_ids"] = [chosen["asset_version_id"]] if chosen.get("asset_version_id") else []
        updated.append(registry.update(row["publication_id"], content=content, package_snapshot=snapshot or row.get("package_snapshot")))
    return updated


def select_image(
    publication_id: str,
    option_id: str,
    *,
    selected_by: str,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    registry: Optional[PublicationRegistry] = None,
) -> list[dict[str, Any]]:
    registry = registry or PublicationRegistry(project, data_root=data_root)
    rows = _group(registry, publication_id)
    options = list((rows[0].get("content") or {}).get("image_options") or [])
    chosen = next((o for o in options if o.get("id") == option_id), None)
    if chosen is None:
        raise ValueError(f"{publication_id} has no image option {option_id!r} (have: {[o.get('id') for o in options]})")
    return _apply(registry, rows, chosen, options=options, by=selected_by)


def upload_image(
    publication_id: str,
    file_path: Path,
    *,
    uploaded_by: str,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    registry: Optional[PublicationRegistry] = None,
    uploader: Any = None,
) -> list[dict[str, Any]]:
    """Harry's own photo (any format Pillow + HEIF reads) becomes option
    U<n> and the selected image."""
    registry = registry or PublicationRegistry(project, data_root=data_root)
    rows = _group(registry, publication_id)
    upload_file = normalize_for_instagram(to_upload_jpeg(Path(file_path)))
    rejection = aspect_ratio_rejection(upload_file)
    if rejection:
        raise ValueError(f"photo cannot be posted to Instagram: {rejection}")
    if uploader is None:
        from shared.storage.google_drive import google_drive_uploader_from_env

        uploader = google_drive_uploader_from_env(os.environ)
    options = list((rows[0].get("content") or {}).get("image_options") or [])
    option_id = f"U{sum(1 for o in options if str(o.get('id', '')).startswith('U')) + 1}"
    url = uploader.upload_and_publish(upload_file, folder_path=["uploads", str(rows[0].get("slot_id") or publication_id)], mimetype="image/jpeg")
    if not url:
        raise RuntimeError("Drive upload returned no URL")
    chosen = image_option_entry(option_id, kind="upload", url=url, source=Path(file_path).name)
    return _apply(registry, rows, chosen, options=[*options, chosen], by=uploaded_by)


_LABELS = {"ai": "AI", "photo": "ảnh thật", "upload": "ảnh tải lên", "fallback": "ảnh dự phòng"}


def notify_image_options(
    *,
    since: str,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    registry: Optional[PublicationRegistry] = None,
    post: Callable[..., dict] = urllib_post,
    token: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> int:
    """One Telegram album per new pending slot created at/after `since`:
    the image options plus the caption, so Harry can decide from his phone
    and pick on the Dashboard. Returns how many slots were sent."""
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return 0
    registry = registry or PublicationRegistry(project, data_root=data_root)
    groups: dict[str, dict[str, Any]] = {}
    for row in registry.load()["publications"]:
        if row.get("status") != PENDING_STATUS or str(row.get("created_at", ""))[:19] < since[:19]:
            continue
        key = f"{row.get('slot_id')}|{row.get('topic')}"
        groups.setdefault(key, row)
    sent = 0
    base = f"https://api.telegram.org/bot{token}"
    for row in sorted(groups.values(), key=lambda r: str(r.get("slot_id"))):
        content = row.get("content") or {}
        options = content.get("image_options") or [{"id": "A", "kind": "ai", "url": content.get("image_public_url")}]
        header = f"🖼️ {row.get('slot_id', '')[5:]} · {row.get('topic')}\nChọn ảnh trên Dashboard → Growth (mặc định {content.get('image_option_selected', 'A')})."
        caption = f"{header}\n\n{str(content.get('text', ''))[:700]}"
        media = [
            {
                "type": "photo",
                "media": o["url"],
                **({"caption": caption[:1024]} if index == 0 else {}),
            }
            for index, o in enumerate(options[:10])
            if o.get("url")
        ]
        legend = " · ".join(f"{o['id']} = {_LABELS.get(o.get('kind'), o.get('kind'))}" for o in options)
        try:
            if len(media) >= 2:
                post(f"{base}/sendMediaGroup", json={"chat_id": chat_id, "media": media}, timeout=60)
            elif media:
                post(f"{base}/sendPhoto", json={"chat_id": chat_id, "photo": media[0]["media"], "caption": caption[:1024]}, timeout=60)
            post(f"{base}/sendMessage", json={"chat_id": chat_id, "text": f"Thứ tự ảnh: {legend}"}, timeout=30)
        except Exception:  # noqa: BLE001 - Telegram cannot fetch some URLs; fall back to plain links
            links = "\n".join(f"{o['id']} ({_LABELS.get(o.get('kind'), o.get('kind'))}): {o.get('url')}" for o in options)
            post(f"{base}/sendMessage", json={"chat_id": chat_id, "text": f"{caption[:3000]}\n\n{links}"}, timeout=30)
        sent += 1
    return sent


def dump(rows: list[dict[str, Any]]) -> str:
    return json.dumps(
        [{"publication_id": r["publication_id"], "image_public_url": (r.get("content") or {}).get("image_public_url"), "image_option_selected": (r.get("content") or {}).get("image_option_selected")} for r in rows],
        ensure_ascii=False,
        indent=2,
    )
