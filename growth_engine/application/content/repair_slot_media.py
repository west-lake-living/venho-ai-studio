from __future__ import annotations

import io
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

from growth_engine.application.media.ingest_asset import IngestAsset


class P4MediaRepairStore(Protocol):
    def load_draft_context(self, local_date: date, channel_key: str) -> Mapping[str, object]: ...
    def find_asset(self, source_ref: str, source_revision: str) -> str | None: ...
    def queue_media(self, context: Mapping[str, object], asset_option: Mapping[str, object], *, now_ms: int) -> Mapping[str, str]: ...


class ImageLibrary(Protocol):
    def read_for_reference(self, reference_id: str, file_id: str) -> Any: ...


class DriveImageIdRequired(ValueError):
    pass


@dataclass(frozen=True)
class P4MediaRepairResult:
    delivery_id: str
    asset_id: str
    source_sha256: str
    prepare_job_id: str | None
    assemble_job_id: str
    requeued: bool


class RepairSlotMedia:
    """Attach one existing or allowlisted Drive image to a P4 DRAFT and requeue media work."""

    def __init__(
        self,
        store: P4MediaRepairStore,
        image_library: ImageLibrary,
        asset_ingestor: IngestAsset,
        clock: Any,
        *,
        environment: str,
    ) -> None:
        self._store = store
        self._image_library = image_library
        self._asset_ingestor = asset_ingestor
        self._clock = clock
        self._environment = environment

    def execute(
        self,
        local_date: date,
        *,
        channel_key: str,
        reference_asset_id: str | None = None,
        drive_file_id: str | None = None,
    ) -> P4MediaRepairResult:
        if self._environment != "production":
            raise ValueError("P4 media repair is restricted to production")
        if channel_key != "fb_hanoi":
            raise ValueError("P4 media repair currently supports fb_hanoi only")
        context = self._store.load_draft_context(local_date, channel_key)
        images = context.get("asset_options")
        option = _existing_option(images)
        if option is None:
            if not reference_asset_id or not drive_file_id:
                raise DriveImageIdRequired(
                    "the DRAFT has no original image; provide its legacy reference asset ID and an allowlisted Drive file ID"
                )
            drive_image = self._image_library.read_for_reference(reference_asset_id, drive_file_id)
            source_ref = f"google-drive:{drive_image.file_id}"
            asset_id = self._store.find_asset(source_ref, drive_image.sha256)
            if asset_id is None:
                asset = self._asset_ingestor.execute(
                    source_type="library",
                    source_ref=source_ref,
                    source_revision=drive_image.sha256,
                    stream=io.BytesIO(drive_image.data),
                    metadata={
                        "source": "allowlisted_google_drive_library",
                        "drive_file_id": drive_image.file_id,
                        "reference_asset_id": reference_asset_id,
                        "source_name": drive_image.name,
                        "mime_type": drive_image.mime_type,
                        "sha256": drive_image.sha256,
                        "p4_repair": True,
                    },
                )
                asset_id = asset.id
                if asset.source_sha256 != drive_image.sha256:
                    raise ValueError("stored P4 media asset SHA-256 differs from the allowlisted Drive source")
            option = {
                "option_id": "C",
                "asset_id": asset_id,
                "sha256": drive_image.sha256,
                "source_type": "library",
                "label": None,
                "provenance": {
                    "source": "allowlisted_google_drive_library",
                    "source_ref": source_ref,
                    "drive_file_id": drive_image.file_id,
                    "reference_asset_id": reference_asset_id,
                    "source_name": drive_image.name,
                    "mime_type": drive_image.mime_type,
                    "dna_subject": "outside",
                    "image_sha256": drive_image.sha256,
                    "p4_repair": True,
                },
            }
        asset_id = option.get("asset_id")
        source_sha = option.get("sha256")
        if not isinstance(asset_id, str) or not asset_id or not isinstance(source_sha, str) or len(source_sha) != 64:
            raise ValueError("existing DRAFT image source has invalid asset identity")
        queued = self._store.queue_media(context, option, now_ms=self._clock.now_ms())
        return P4MediaRepairResult(
            delivery_id=str(context["delivery_id"]),
            asset_id=asset_id,
            source_sha256=source_sha,
            prepare_job_id=queued.get("prepare_job_id"),
            assemble_job_id=str(queued["assemble_job_id"]),
            requeued=bool(queued.get("requeued", True)),
        )


def _existing_option(value: object) -> dict[str, object] | None:
    if not isinstance(value, list):
        return None
    for option_id in ("A", "C", "FALLBACK"):
        for option in value:
            if not isinstance(option, dict) or str(option.get("option_id", "")).upper() != option_id:
                continue
            if isinstance(option.get("asset_id"), str) and isinstance(option.get("sha256"), str):
                return dict(option)
    return None
