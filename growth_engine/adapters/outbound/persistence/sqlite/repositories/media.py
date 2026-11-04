from __future__ import annotations

from growth_engine.domain.media.asset import MediaAsset, MediaVariant, VariantQcStatus
from growth_engine.domain.media.qc import QcDecision, QcReport

from ._base import SqliteRepository, canonical_json, canonical_json_text, parse_json


class MediaRepository(SqliteRepository):
    def save_asset(self, asset: MediaAsset) -> None:
        self.connection.execute(
            """INSERT INTO media_assets
               (id, source_type, source_ref, source_revision, source_sha256, original_key,
                metadata_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                asset.id,
                asset.source_type,
                asset.source_ref,
                asset.source_revision,
                asset.source_sha256,
                asset.original_key,
                canonical_json_text(asset.metadata_json),
                asset.created_at_ms,
            ),
        )

    def get_asset(self, asset_id: str) -> MediaAsset | None:
        row = self.connection.execute(
            """SELECT id, source_type, source_ref, source_revision, source_sha256, original_key,
                      metadata_json, created_at
               FROM media_assets WHERE id=?""",
            (asset_id,),
        ).fetchone()
        if row is None:
            return None
        return MediaAsset(
            id=row["id"],
            source_type=row["source_type"],
            source_ref=row["source_ref"],
            source_revision=row["source_revision"],
            source_sha256=row["source_sha256"],
            original_key=row["original_key"],
            metadata_json=row["metadata_json"],
            created_at_ms=row["created_at"],
        )

    def save_variant(self, variant: MediaVariant) -> None:
        self.connection.execute(
            """INSERT INTO media_variants
               (id, asset_id, transform_version, sha256, object_key, width, height, mime,
                byte_size, qc_status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                variant.id,
                variant.asset_id,
                variant.transform_version,
                variant.sha256,
                variant.object_key,
                variant.width,
                variant.height,
                variant.mime,
                variant.byte_size,
                variant.qc_status.value,
                variant.created_at_ms,
            ),
        )

    def get_variant(self, variant_id: str) -> MediaVariant | None:
        row = self.connection.execute(
            """SELECT id, asset_id, transform_version, sha256, object_key, width, height,
                      mime, byte_size, qc_status, created_at
               FROM media_variants WHERE id=?""",
            (variant_id,),
        ).fetchone()
        if row is None:
            return None
        return MediaVariant(
            id=row["id"],
            asset_id=row["asset_id"],
            transform_version=row["transform_version"],
            sha256=row["sha256"],
            object_key=row["object_key"],
            width=row["width"],
            height=row["height"],
            mime=row["mime"],
            byte_size=row["byte_size"],
            qc_status=VariantQcStatus(row["qc_status"]),
            created_at_ms=row["created_at"],
        )


class QcRepository(SqliteRepository):
    def save(self, report: QcReport) -> None:
        self.connection.execute(
            """INSERT INTO qc_reports
               (id, variant_id, caption_hash, ruleset_hash, fact_snapshot_hash, decision,
                coverage_gaps_json, result_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                report.id,
                report.variant_id,
                report.caption_hash,
                report.ruleset_hash,
                report.fact_snapshot_hash,
                report.decision.value,
                canonical_json(list(report.coverage_gaps)),
                canonical_json_text(report.result_json),
                report.created_at_ms,
            ),
        )

    def get(self, report_id: str) -> QcReport | None:
        row = self.connection.execute(
            """SELECT id, variant_id, caption_hash, ruleset_hash, fact_snapshot_hash, decision,
                      coverage_gaps_json, result_json, created_at
               FROM qc_reports WHERE id=?""",
            (report_id,),
        ).fetchone()
        if row is None:
            return None
        return QcReport(
            id=row["id"],
            variant_id=row["variant_id"],
            caption_hash=row["caption_hash"],
            ruleset_hash=row["ruleset_hash"],
            fact_snapshot_hash=row["fact_snapshot_hash"],
            decision=QcDecision(row["decision"]),
            coverage_gaps=tuple(parse_json(row["coverage_gaps_json"])),
            result_json=row["result_json"],
            created_at_ms=row["created_at"],
        )
