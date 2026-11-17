from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date
from typing import Any, Callable

from growth_engine.domain.kernel.hashing import canonical_json_bytes, sha256_hex


class SqliteP4MediaRepairStore:
    def __init__(
        self,
        uow_factory: Callable[[], Any],
        ids: Any,
        *,
        environment: str,
        transform_version_for_facebook: str,
    ) -> None:
        self._uow_factory = uow_factory
        self._ids = ids
        self._environment = environment
        self._transform_version = transform_version_for_facebook

    def load_draft_context(self, local_date: date, channel_key: str) -> Mapping[str, object]:
        if self._environment != "production" or channel_key != "fb_hanoi":
            raise ValueError("P4 media repair is production fb_hanoi only")
        with self._uow_factory().read_only() as tx:
            controls = tx.controls.get("production")
            if controls is None or controls.mode.value != "DISABLED" or not controls.global_pause:
                raise ValueError("P4 repair requires runtime DISABLED and global_pause=1")
            row = _load_target(tx.connection, local_date, channel_key)
            _assert_repairable(tx.connection, row)
            package = json.loads(str(row["source_snapshot_json"]))
            images = package.get("images", [])
            if not isinstance(images, list):
                images = []
            return {
                "delivery_id": str(row["delivery_id"]),
                "package_id": str(row["package_id"]),
                "channel_key": channel_key,
                "slot_date": str(row["local_date"]),
                "slot_time": str(row["local_time"]),
                "asset_options": images,
            }

    def find_asset(self, source_ref: str, source_revision: str) -> str | None:
        with self._uow_factory().read_only() as tx:
            row = tx.connection.execute(
                """SELECT id FROM media_assets
                   WHERE source_type='library' AND source_ref=? AND source_revision=?""",
                (source_ref, source_revision),
            ).fetchone()
        return None if row is None else str(row["id"])

    def queue_media(
        self,
        context: Mapping[str, object],
        asset_option: Mapping[str, object],
        *,
        now_ms: int,
    ) -> Mapping[str, str]:
        delivery_id = str(context.get("delivery_id") or "")
        asset_id = str(asset_option.get("asset_id") or "")
        source_sha = str(asset_option.get("sha256") or "")
        if not delivery_id or not asset_id or len(source_sha) != 64:
            raise ValueError("P4 repair identity is incomplete")
        asset_options_json = canonical_json_bytes([dict(asset_option)]).decode("utf-8")
        with self._uow_factory().begin_immediate() as tx:
            controls = tx.controls.get("production")
            if controls is None or controls.mode.value != "DISABLED" or not controls.global_pause:
                raise ValueError("P4 repair requires runtime DISABLED and global_pause=1")
            row = tx.connection.execute(
                """SELECT d.id AS delivery_id, d.state, d.active, d.current_revision_id,
                          d.package_id, d.target_id, c.id AS channel_id, c.channel_key,
                          c.platform, c.remote_account_id, cc.id AS channel_config_id,
                          cc.caption_profile, s.local_date, s.local_time,
                          p.source_snapshot_json
                   FROM deliveries d JOIN channels c ON c.id=d.channel_id
                   JOIN slot_targets st ON st.id=d.target_id AND st.channel_id=d.channel_id
                   JOIN slots s ON s.id=st.slot_id JOIN content_packages p ON p.id=d.package_id
                   JOIN channel_configs cc ON cc.channel_id=c.id
                   WHERE d.id=? AND c.environment='production'
                   ORDER BY cc.version DESC LIMIT 1""",
                (delivery_id,),
            ).fetchone()
            if row is None:
                raise ValueError("P4 delivery disappeared before media requeue")
            _assert_repairable(tx.connection, row)
            if (
                str(row["local_date"]) != str(context.get("slot_date"))
                or str(row["local_time"]) != str(context.get("slot_time"))
            ):
                raise ValueError("P4 slot changed before media requeue")
            if str(row["channel_key"]) != "fb_hanoi" or str(row["remote_account_id"]) != "1124616474074140":
                raise ValueError("P4 delivery no longer maps to the Hanoi Facebook Page")
            asset = tx.media.get_asset(asset_id)
            if asset is None or asset.source_sha256 != source_sha:
                raise ValueError("P4 media asset is missing or its SHA-256 changed")
            slot_date = date.fromisoformat(str(row["local_date"]))
            slot_id = str(tx.connection.execute(
                "SELECT slot_id FROM slot_targets WHERE id=?", (row["target_id"],)
            ).fetchone()[0])
            business_key = f"prepare-variant:{asset_id}:facebook_photo_v1"
            prepare = tx.connection.execute(
                "SELECT id,state FROM jobs WHERE kind='prepare_variant' AND business_key=?",
                (business_key,),
            ).fetchone()
            prepare_job_id: str | None = None
            variant = tx.connection.execute(
                """SELECT id FROM media_variants WHERE asset_id=? AND transform_version=?
                   ORDER BY created_at DESC LIMIT 1""",
                (asset_id, self._transform_version),
            ).fetchone()
            if variant is None:
                prepare_payload = canonical_json_bytes({
                    "asset_id": asset_id,
                    "option_id": asset_option.get("option_id", "C"),
                    "media_profile": "facebook_photo_v1",
                }).decode("utf-8")
                if prepare is None:
                    prepare_job_id = self._ids.new_id()
                    tx.connection.execute(
                        """INSERT INTO jobs
                           (id,kind,lane,business_key,payload_json,state,run_at,created_at,updated_at)
                           VALUES (?,'prepare_variant','jobs',?,?,'PENDING',?,?,?)""",
                        (prepare_job_id, business_key, prepare_payload, now_ms, now_ms, now_ms),
                    )
                else:
                    prepare_job_id = str(prepare["id"])
                    if str(prepare["state"]) == "RUNNING":
                        pass
                    else:
                        tx.connection.execute(
                            """UPDATE jobs SET payload_json=?,state='PENDING',run_at=?,last_error=NULL,
                                      lease_owner=NULL,lease_token=NULL,lease_until=NULL,updated_at=?
                               WHERE id=?""",
                            (prepare_payload, now_ms, now_ms, prepare_job_id),
                        )

            snapshot = json.loads(str(row["source_snapshot_json"]))
            assemble_payload = canonical_json_bytes({
                "delivery_id": delivery_id,
                "package_id": str(row["package_id"]),
                "channel_config_id": str(row["channel_config_id"]),
                "channel_key": "fb_hanoi",
                "platform": "facebook",
                "media_profile": "facebook_photo_v1",
                "caption_profile": str(row["caption_profile"] or "default"),
                "captions_by_profile": snapshot.get("captions_by_profile", {}),
                "asset_options": [dict(asset_option)],
            }).decode("utf-8")
            assemble_key = f"assemble-revision:{delivery_id}:1"
            assemble = tx.connection.execute(
                "SELECT id,state FROM jobs WHERE kind='assemble_revision' AND business_key=?",
                (assemble_key,),
            ).fetchone()
            if assemble is None:
                assemble_job_id = self._ids.new_id()
                tx.connection.execute(
                    """INSERT INTO jobs
                       (id,kind,lane,business_key,payload_json,state,run_at,created_at,updated_at)
                       VALUES (?,'assemble_revision','jobs',?,?,'PENDING',?,?,?)""",
                    (assemble_job_id, assemble_key, assemble_payload, now_ms, now_ms, now_ms),
                )
                requeued = False
            else:
                assemble_job_id = str(assemble["id"])
                if str(assemble["state"]) == "RUNNING":
                    raise ValueError("assemble_revision is currently running; retry after it releases its lease")
                tx.connection.execute(
                    """UPDATE jobs SET payload_json=?,state='PENDING',run_at=?,last_error=NULL,
                              lease_owner=NULL,lease_token=NULL,lease_until=NULL,updated_at=?
                       WHERE id=?""",
                    (assemble_payload, now_ms, now_ms, assemble_job_id),
                )
                requeued = True
            before_hash = sha256_hex(canonical_json_bytes({
                "delivery_id": delivery_id,
                "state": str(row["state"]),
                "package_id": str(row["package_id"]),
            }))
            after_hash = sha256_hex(canonical_json_bytes({
                "delivery_id": delivery_id,
                "asset_id": asset_id,
                "source_sha256": source_sha,
                "prepare_job_id": prepare_job_id,
                "assemble_job_id": assemble_job_id,
            }))
            tx.audit.append(
                event_id=self._ids.new_id(),
                aggregate_type="delivery",
                aggregate_id=delivery_id,
                actor="growth-engine-operator",
                action="delivery.p4_media_requeued",
                before_hash=before_hash,
                after_hash=after_hash,
                details_json=json.dumps({
                    "slot_id": slot_id,
                    "local_date": slot_date.isoformat(),
                    "channel_key": "fb_hanoi",
                    "asset_id": asset_id,
                    "source_sha256": source_sha,
                    "prepare_job_id": prepare_job_id,
                    "assemble_job_id": assemble_job_id,
                }, separators=(",", ":")),
                correlation_id=f"p4-media-repair:{delivery_id}:{source_sha}",
                created_at_ms=now_ms,
            )
        result = {"assemble_job_id": assemble_job_id, "requeued": str(requeued).lower()}
        if prepare_job_id is not None:
            result["prepare_job_id"] = prepare_job_id
        return result


def _load_target(connection: Any, local_date: date, channel_key: str):
    row = connection.execute(
        """SELECT d.id AS delivery_id, d.state, d.active, d.current_revision_id,
                  d.package_id, d.target_id, c.id AS channel_id, c.channel_key,
                  c.platform, c.remote_account_id, p.source_snapshot_json,
                  s.local_date, s.local_time
           FROM deliveries d JOIN channels c ON c.id=d.channel_id
           JOIN slot_targets st ON st.id=d.target_id AND st.channel_id=d.channel_id
           JOIN slots s ON s.id=st.slot_id JOIN content_packages p ON p.id=d.package_id
           WHERE c.environment='production' AND c.channel_key=?
             AND s.local_date=? AND s.local_time='09:00' AND d.active=1
           ORDER BY d.created_at DESC LIMIT 1""",
        (channel_key, local_date.isoformat()),
    ).fetchone()
    if row is None:
        raise ValueError("no active DRAFT delivery exists for the requested P4 slot")
    return row


def _assert_repairable(connection: Any, row: Any) -> None:
    if str(row["state"]) != "DRAFT" or not bool(row["active"]) or row["current_revision_id"] is not None:
        raise ValueError("P4 repair only accepts an active DRAFT without a revision")
    if str(row["channel_key"]) != "fb_hanoi" or str(row["platform"]) != "facebook":
        raise ValueError("P4 repair only accepts the fb_hanoi Facebook target")
    if str(row["remote_account_id"]) != "1124616474074140":
        raise ValueError("P4 target is not mapped to Page 1124616474074140")
    command_count = int(connection.execute(
        "SELECT count(*) FROM outbox_commands WHERE delivery_id=?", (row["delivery_id"],)
    ).fetchone()[0])
    execution_count = int(connection.execute(
        "SELECT count(*) FROM executions WHERE delivery_id=?", (row["delivery_id"],)
    ).fetchone()[0])
    if command_count or execution_count:
        raise ValueError("P4 DRAFT has dispatch artifacts; media repair is blocked")
