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
    @property
    def allowed_reference_ids(self) -> frozenset[str]: ...

    def resolve(self, reference_id: str, rotation_key: str, rotation_offset: int = 0) -> Any: ...


class LegacyImageGroupRequired(ValueError):
    pass


@dataclass(frozen=True)
class P4MediaRepairResult:
    delivery_id: str
    asset_id: str
    source_sha256: str
    source_relative_path: str
    reference_asset_id: str | None
    prepare_job_id: str | None
    assemble_job_id: str
    requeued: bool


class RepairSlotMedia:
    """Attach one hash-pinned legacy local image to a P4 DRAFT and requeue media work."""

    def __init__(
        self,
        store: P4MediaRepairStore,
        image_library: ImageLibrary,
        asset_ingestor: IngestAsset,
        clock: Any,
        *,
        environment: str,
        reference_subjects: Mapping[str, str],
    ) -> None:
        self._store = store
        self._image_library = image_library
        self._asset_ingestor = asset_ingestor
        self._clock = clock
        self._environment = environment
        self._reference_subjects = dict(reference_subjects)

    @property
    def allowed_reference_ids(self) -> frozenset[str]:
        return frozenset(self._image_library.allowed_reference_ids).intersection(self._reference_subjects)

    def preview_context(self, local_date: date, *, channel_key: str) -> Mapping[str, str]:
        self._assert_target(channel_key)
        context = self._store.load_draft_context(local_date, channel_key)
        return {
            "delivery_id": str(context["delivery_id"]),
            "topic_key": str(context.get("topic_key") or ""),
            "brief": str(context.get("brief") or ""),
        }

    def execute(
        self,
        local_date: date,
        *,
        channel_key: str,
        reference_asset_id: str | None = None,
    ) -> P4MediaRepairResult:
        self._assert_target(channel_key)
        context = self._store.load_draft_context(local_date, channel_key)
        images = context.get("asset_options")
        option = _existing_option(images)
        if option is None:
            if not reference_asset_id:
                raise LegacyImageGroupRequired(
                    "the DRAFT has no original image; choose its existing legacy reference group"
                )
            library_image = self._image_library.resolve(reference_asset_id, local_date.isoformat(), 1)
            if library_image is None:
                raise ValueError("selected legacy reference group has no allowlisted image")
            dna_subject = self._reference_subjects.get(reference_asset_id)
            if not dna_subject:
                raise ValueError("selected legacy reference group is not linked to a catalog scenario")
            source_ref = f"legacy-local:{library_image.relative_path}"
            asset_id = self._store.find_asset(source_ref, library_image.sha256)
            if asset_id is None:
                asset = self._asset_ingestor.execute(
                    source_type="library",
                    source_ref=source_ref,
                    source_revision=library_image.sha256,
                    stream=io.BytesIO(library_image.data),
                    metadata={
                        "source": "local_legacy_library",
                        "relative_path": library_image.relative_path,
                        "reference_asset_id": reference_asset_id,
                        "source_name": library_image.name,
                        "mime_type": library_image.mime_type,
                        "sha256": library_image.sha256,
                        "p4_repair": True,
                    },
                )
                asset_id = asset.id
                if asset.source_sha256 != library_image.sha256:
                    raise ValueError("stored P4 media asset SHA-256 differs from the allowlisted local source")
            option = {
                "option_id": "C",
                "asset_id": asset_id,
                "sha256": library_image.sha256,
                "source_type": "library",
                "label": None,
                "provenance": {
                    "source": "local_legacy_library",
                    "source_ref": source_ref,
                    "relative_path": library_image.relative_path,
                    "reference_asset_id": reference_asset_id,
                    "source_name": library_image.name,
                    "mime_type": library_image.mime_type,
                    "dna_subject": dna_subject,
                    "image_sha256": library_image.sha256,
                    "p4_repair": True,
                },
            }
        asset_id = option.get("asset_id")
        source_sha = option.get("sha256")
        provenance = option.get("provenance")
        source_relative_path = provenance.get("relative_path") if isinstance(provenance, dict) else None
        if (
            not isinstance(asset_id, str) or not asset_id
            or not isinstance(source_sha, str) or len(source_sha) != 64
            or not isinstance(source_relative_path, str) or not source_relative_path
        ):
            raise ValueError("existing DRAFT image source has invalid asset identity")
        queued = self._store.queue_media(context, option, now_ms=self._clock.now_ms())
        return P4MediaRepairResult(
            delivery_id=str(context["delivery_id"]),
            asset_id=asset_id,
            source_sha256=source_sha,
            source_relative_path=source_relative_path,
            reference_asset_id=reference_asset_id if provenance.get("p4_repair") else None,
            prepare_job_id=queued.get("prepare_job_id"),
            assemble_job_id=str(queued["assemble_job_id"]),
            requeued=bool(queued.get("requeued", True)),
        )

    def _assert_target(self, channel_key: str) -> None:
        if self._environment != "production":
            raise ValueError("P4 media repair is restricted to production")
        if channel_key != "fb_hanoi":
            raise ValueError("P4 media repair currently supports fb_hanoi only")


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
