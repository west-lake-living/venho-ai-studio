from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Mapping, Sequence
from zoneinfo import ZoneInfo

import yaml

from shared.meta.graph_client import MetaGraphError, ReadOnlyGraphClient
from shared.meta.metric_capabilities import capability_state
from shared.notify.telegram import TelegramNotifier


CHANNEL_FOR_PLATFORM = {"facebook": "fb_hanoi", "instagram": "ig_venho"}
VALUE_STATES = {"VALUE", "ZERO", "NULL", "UNAVAILABLE", "ERROR"}
METRIC_SCHEMA = """
CREATE TABLE IF NOT EXISTS metric_observations (
  id TEXT PRIMARY KEY,
  delivery_id TEXT NOT NULL,
  metric TEXT NOT NULL,
  checkpoint TEXT NOT NULL CHECK(checkpoint IN ('24h','72h','7d','adhoc')),
  observed_at INTEGER NOT NULL,
  post_age_seconds INTEGER NOT NULL CHECK(post_age_seconds >= 0),
  value INTEGER,
  value_state TEXT NOT NULL CHECK(value_state IN ('VALUE','ZERO','NULL','UNAVAILABLE','ERROR')),
  source TEXT NOT NULL CHECK(source IN ('meta_graph','mock')),
  api_version TEXT NOT NULL,
  period TEXT,
  dimensions_json TEXT NOT NULL DEFAULT '{}',
  error_code TEXT,
  UNIQUE(delivery_id, metric, checkpoint, observed_at, source),
  CHECK(value_state NOT IN ('VALUE','ZERO') OR value IS NOT NULL),
  CHECK(value_state != 'ZERO' OR value = 0),
  CHECK(value_state IN ('VALUE','ZERO') OR value IS NULL)
)
"""


def _parse_time(value: object, *, timezone_name: str = "Asia/Ho_Chi_Minh") -> int | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(timezone_name))
    return int(parsed.timestamp() * 1000)


def _image_kind(content: Mapping[str, Any]) -> str:
    if content.get("image_is_fallback") is True:
        return "fallback"
    source = str(content.get("image_source") or content.get("source_type") or "").casefold()
    if "upload" in source:
        return "upload"
    if "real" in source or "photo" in source:
        return "real"
    if content.get("image_run_path"):
        return "AI"
    return "unknown"


def load_targets(
    *,
    registry_path: Path,
    reconcile_dir: Path,
    days: int,
    now_ms: int,
    timezone_name: str = "Asia/Ho_Chi_Minh",
) -> list[dict[str, Any]]:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(registry, dict) or not isinstance(registry.get("publications"), list):
        raise ValueError("publication registry has an invalid shape")
    earliest = now_ms - days * 24 * 60 * 60 * 1000
    targets: dict[tuple[str, str], dict[str, Any]] = {}
    for row in registry["publications"]:
        if row.get("status") != "PUBLISHED" or not row.get("platform_post_id"):
            continue
        channel_id = CHANNEL_FOR_PLATFORM.get(str(row.get("platform")))
        if channel_id is None:
            continue
        published_at = _parse_time(row.get("published_at") or row.get("updated_at") or row.get("created_at"), timezone_name=timezone_name)
        if published_at is None or published_at < earliest or published_at > now_ms:
            continue
        content = row.get("content") if isinstance(row.get("content"), dict) else {}
        publication_id = str(row.get("publication_id") or row.get("content_package_id") or row["platform_post_id"])
        targets[(channel_id, str(row["platform_post_id"]))] = {
            "channel_id": channel_id,
            "delivery_id": publication_id,
            "post_id": str(row["platform_post_id"]),
            "published_at_ms": published_at,
            "api_version": "",
            "pillar": str(row.get("pillar") or "unknown"),
            "image_kind": _image_kind(content),
            "manual": False,
            "reconcile_status": "TRACKED",
        }
    if reconcile_dir.exists():
        for path in sorted(reconcile_dir.glob("*.json")):
            if path.name == "alerted.json":
                continue
            try:
                report = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for row in report.get("results", []):
                channel_id = row.get("channel_id")
                post_id = row.get("post_id")
                status = str(row.get("status") or "")
                published_at = row.get("created_at_ms")
                if channel_id != "fb_venho" or not post_id or status not in {"UNTRACKED", "CAPTION_DIFF"}:
                    continue
                if type(published_at) is not int or published_at < earliest or published_at > now_ms:
                    continue
                key = (channel_id, str(post_id))
                targets[key] = {
                    "channel_id": channel_id,
                    "delivery_id": f"manual:{channel_id}:{post_id}",
                    "post_id": str(post_id),
                    "published_at_ms": published_at,
                    "api_version": "",
                    "pillar": "unknown",
                    "image_kind": "unknown",
                    "manual": True,
                    "reconcile_status": status,
                }
    return list(targets.values())


def _verified_metric_specs(registry_path: Path, channel_id: str) -> list[dict[str, Any]]:
    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    result: list[dict[str, Any]] = []
    for metric in payload.get("metrics", []):
        channel_values = metric.get("channels")
        if isinstance(channel_values, list) and channel_id not in channel_values:
            continue
        channel_spec = channel_values.get(channel_id) if isinstance(channel_values, dict) else None
        spec = channel_spec if isinstance(channel_spec, dict) else metric
        if str(spec.get("availability", metric.get("availability", ""))).upper() not in {"VERIFIED", "AVAILABLE", "READABLE"}:
            if str(spec.get("availability", metric.get("availability", ""))).upper() != "CONDITIONAL":
                continue
        name = str(spec.get("name") or metric.get("name") or "").strip()
        provider_field = str(spec.get("provider_field") or "").strip()
        period = spec.get("period")
        scope = str(spec.get("scope") or metric.get("scope") or "post").strip()
        capability = spec.get("capability") or metric.get("capability")
        if scope == "post_field" and not capability:
            continue
        if capability and capability_state(payload, str(capability), channel_id) != "SUPPORTED":
            continue
        if not name or not provider_field or "REQUIRED_FROM_P0" in provider_field:
            continue
        if period is not None and not isinstance(period, str):
            continue
        result.append(
            {
                "name": name,
                "provider_field": provider_field,
                "period": period,
                "scope": scope,
                "missing_value_state": spec.get("missing_value_state", metric.get("missing_value_state")),
            }
        )
    return result


def _client_for(channel_id: str, candidates_path: Path, env: Mapping[str, str]) -> tuple[ReadOnlyGraphClient, str]:
    payload = yaml.safe_load(candidates_path.read_text(encoding="utf-8")) or {}
    candidate = (payload.get("channels") or {}).get(channel_id)
    if not isinstance(candidate, dict):
        raise ValueError(f"Meta candidate config is missing {channel_id}")
    token_env = str(candidate.get("token_env") or "")
    token = env.get(token_env, "").strip()
    if not token:
        raise ValueError(f"required environment variable {token_env} is empty")
    return ReadOnlyGraphClient(
        api_version=str(candidate.get("api_version") or payload.get("api_version") or ""),
        access_token=token,
        collection_edge=str(candidate.get("collection_edge") or "posts"),
    ), str(candidate.get("api_version") or payload.get("api_version") or "")


def _read_one_metric(client: Any, target: Mapping[str, Any], spec: Mapping[str, Any]) -> tuple[int | None, str, str | None]:
    if spec.get("scope") == "post_field":
        return _read_one_post_field(client, target, spec)
    try:
        payload = client.get_insights(str(target["post_id"]), [str(spec["provider_field"])], spec.get("period"))
    except MetaGraphError as error:
        return _metric_error(error)
    except Exception:
        return None, "ERROR", "SOURCE_ERROR"
    data = payload.get("data")
    if not isinstance(data, list):
        return None, "ERROR", "INVALID_RESPONSE"
    item = next((row for row in data if isinstance(row, dict) and row.get("name") == spec["provider_field"]), None)
    if item is None:
        return None, "UNAVAILABLE", None
    values = item.get("values")
    if not isinstance(values, list) or not values:
        return None, "NULL", None
    latest = values[-1]
    if not isinstance(latest, dict) or "value" not in latest:
        return None, "ERROR", "INVALID_RESPONSE"
    value = latest["value"]
    if value is None:
        return None, "NULL", None
    if type(value) is not int or value < 0:
        return None, "ERROR", "INVALID_VALUE"
    return value, "ZERO" if value == 0 else "VALUE", None


def _read_one_post_field(
    client: Any, target: Mapping[str, Any], spec: Mapping[str, Any]
) -> tuple[int | None, str, str | None]:
    provider_field = str(spec["provider_field"])
    root_field = provider_field.split(".", 1)[0]
    try:
        payload = client.get_object(str(target["post_id"]), [provider_field])
    except MetaGraphError as error:
        return _metric_error(error)
    except Exception:
        return None, "ERROR", "SOURCE_ERROR"
    if not isinstance(payload, dict):
        return None, "ERROR", "INVALID_RESPONSE"

    field_value = payload.get(root_field)
    if field_value is None:
        if str(spec.get("missing_value_state") or "").upper() == "ZERO":
            return 0, "ZERO", None
        return None, "UNAVAILABLE", None
    if root_field in {"reactions", "comments"}:
        summary = field_value.get("summary") if isinstance(field_value, dict) else None
        value = summary.get("total_count") if isinstance(summary, dict) else None
        if value is None:
            return None, "UNAVAILABLE", None
    elif root_field == "shares":
        value = field_value.get("count") if isinstance(field_value, dict) else None
        if value is None:
            if str(spec.get("missing_value_state") or "").upper() == "ZERO":
                return 0, "ZERO", None
            return None, "UNAVAILABLE", None
    else:
        value = field_value
    if type(value) is not int or value < 0:
        return None, "ERROR", "INVALID_VALUE"
    return value, "ZERO" if value == 0 else "VALUE", None


def _metric_error(error: MetaGraphError) -> tuple[int | None, str, str | None]:
    if error.provider_code is not None:
        return None, "UNAVAILABLE", f"META_CODE_{error.provider_code}"
    if error.kind is None:
        return None, "UNAVAILABLE", "UNSUPPORTED" if error.status == 400 else f"META_HTTP_{error.status or 'UNKNOWN'}"
    return None, "ERROR", f"META_{error.kind.value}"


def _observation_id(delivery_id: str, metric: str, observed_at_ms: int) -> str:
    key = f"{delivery_id}\0{metric}\0adhoc\0{observed_at_ms}\0meta_graph"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


def _ensure_external_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(METRIC_SCHEMA)
    return connection


def backfill_insights(
    *,
    days: int = 90,
    project: str = "venho_hotel",
    config_root: Path = Path("config/projects/venho_hotel"),
    data_root: Path = Path("data/projects"),
    reports_root: Path | None = None,
    metrics_registry_path: Path | None = None,
    now: datetime | None = None,
    env: Mapping[str, str] | None = None,
    client_factory: Callable[[str, Path, Mapping[str, str]], tuple[Any, str]] = _client_for,
) -> dict[str, Any]:
    if not 1 <= days <= 365:
        raise ValueError("days must be between 1 and 365")
    environment = env or os.environ
    root = reports_root or Path(environment.get("GE_GROWTH_REPORTS_DIR", "~/venho/state/growth-reports")).expanduser()
    now_dt = now or datetime.now(timezone.utc)
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
    now_ms = int(now_dt.timestamp() * 1000)
    channels_doc = yaml.safe_load((config_root / "growth_engine" / "channels.yaml").read_text(encoding="utf-8")) or {}
    channels = {str(row.get("channel_id")): row for row in channels_doc.get("channels", []) if row.get("environment") == "production"}
    timezone_name = str(channels_doc.get("timezone") or "Asia/Ho_Chi_Minh")
    reconcile_dir = root / "channel_reconcile"
    registry_path = data_root / project / "publishing" / "publication_registry.json"
    targets = load_targets(registry_path=registry_path, reconcile_dir=reconcile_dir, days=days, now_ms=now_ms, timezone_name=timezone_name)
    metrics_path = metrics_registry_path or (config_root / "growth_engine" / "metrics_registry.yaml")
    candidates_path = config_root / "growth_engine" / "meta_probe_candidates.yaml"
    database_path = root / "insights.db"
    output_dir = root / "insights"
    observed_at_ms = (now_ms // 60_000) * 60_000
    inserted = 0
    skipped: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    with closing(_ensure_external_db(database_path)) as connection:
        for target in targets:
            channel = channels.get(target["channel_id"])
            if not channel:
                skipped.append({"delivery_id": target["delivery_id"], "reason": "channel_not_configured"})
                continue
            remote_id = channel.get("remote_page_id") or channel.get("remote_account_id")
            if not remote_id:
                skipped.append({"delivery_id": target["delivery_id"], "reason": "missing_remote_account_id"})
                continue
            specs = _verified_metric_specs(metrics_path, target["channel_id"])
            if not specs:
                skipped.append({"delivery_id": target["delivery_id"], "reason": "no_verified_metrics"})
                continue
            try:
                client, api_version = client_factory(target["channel_id"], candidates_path, environment)
            except (OSError, ValueError, KeyError, TypeError) as error:
                errors.append({"delivery_id": target["delivery_id"], "reason": str(error)})
                continue
            target["api_version"] = api_version
            dimensions = json.dumps(
                {key: target[key] for key in ("channel_id", "pillar", "image_kind", "manual")},
                ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            )
            age_seconds = max(0, (observed_at_ms - int(target["published_at_ms"])) // 1000)
            for spec in specs:
                value, state, error_code = _read_one_metric(client, target, spec)
                if state not in VALUE_STATES:
                    state = "ERROR"
                row_id = _observation_id(str(target["delivery_id"]), str(spec["name"]), observed_at_ms)
                cursor = connection.execute(
                    """INSERT OR IGNORE INTO metric_observations
                       (id, delivery_id, metric, checkpoint, observed_at, post_age_seconds, value,
                        value_state, source, api_version, period, dimensions_json, error_code)
                       VALUES (?, ?, ?, 'adhoc', ?, ?, ?, ?, 'meta_graph', ?, ?, ?, ?)""",
                    (row_id, target["delivery_id"], spec["name"], observed_at_ms, age_seconds, value,
                     state, api_version, spec.get("period"), dimensions, error_code),
                )
                inserted += cursor.rowcount
        connection.commit()
    output_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": "growth.insights-backfill.v1",
        "generated_at": now_dt.isoformat(),
        "days": days,
        "database": str(database_path),
        "targets": len(targets),
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors,
    }
    report_path = output_dir / f"backfill-{now_dt.date().isoformat()}.json"
    _write_json(report_path, record)
    return record


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def insights_report(
    *,
    reports_root: Path | None = None,
    metrics_registry_path: Path | None = None,
    env: Mapping[str, str] | None = None,
    minimum_samples: int = 5,
    send_telegram: bool = False,
    telegram_notifier: TelegramNotifier | None = None,
    telegram_chat_id: str | None = None,
    now: datetime | None = None,
) -> Path:
    if minimum_samples < 1:
        raise ValueError("minimum_samples must be positive")
    environment = env or os.environ
    root = reports_root or Path(environment.get("GE_GROWTH_REPORTS_DIR", "~/venho/state/growth-reports")).expanduser()
    registry_path = metrics_registry_path or Path("config/projects/venho_hotel/growth_engine/metrics_registry.yaml")
    try:
        metric_registry = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    except OSError:
        metric_registry = {}
    database_path = root / "insights.db"
    zone = ZoneInfo("Asia/Ho_Chi_Minh")
    current = now or datetime.now(zone)
    if not database_path.exists():
        raise FileNotFoundError("Track 0 insights database does not exist")
    with closing(sqlite3.connect(database_path)) as connection:
        rows = connection.execute(
            """SELECT delivery_id, metric, observed_at, value, value_state, dimensions_json
               FROM metric_observations WHERE source='meta_graph' ORDER BY observed_at DESC"""
        ).fetchall()
    latest: dict[tuple[str, str], tuple[Any, ...]] = {}
    for row in rows:
        latest.setdefault((row[0], row[1]), row)
    grouped: dict[tuple[str, str, str], list[tuple[Any, ...]]] = defaultdict(list)
    metadata: dict[tuple[str, str], dict[str, Any]] = {}
    for row in latest.values():
        try:
            dims = json.loads(row[5])
        except (TypeError, json.JSONDecodeError):
            continue
        key = (str(dims.get("channel_id", "unknown")), str(dims.get("pillar", "unknown")), str(dims.get("image_kind", "unknown")))
        grouped[key].append(row)
        metadata[(key[0], row[0])] = dims
    sections: list[dict[str, Any]] = []
    markdown = [f"# Growth Insights — {current.date().isoformat()}", "", "Source: read-only Meta Graph backfill in `~/venho/state/growth-reports/insights.db`.", ""]
    for key in sorted(grouped):
        channel_id, pillar, image_kind = key
        observations = grouped[key]
        delivery_ids = sorted({row[0] for row in observations})
        sample_count = len(delivery_ids)
        manual_ids = sorted(delivery_id for delivery_id in delivery_ids if metadata.get((channel_id, delivery_id), {}).get("manual"))
        metrics: list[dict[str, Any]] = []
        for metric in sorted({row[1] for row in observations}):
            values = [row[3] for row in observations if row[1] == metric and row[4] in {"VALUE", "ZERO"} and row[3] is not None]
            states = Counter(row[4] for row in observations if row[1] == metric)
            metric_row: dict[str, Any] = {"metric": metric, "sample_count": len(values), "states": dict(states)}
            if sample_count >= minimum_samples and len(values) >= minimum_samples:
                metric_row["average"] = round(mean(values), 2)
            else:
                metric_row["values"] = values
            metrics.append(metric_row)
        section = {
            "channel_id": channel_id, "pillar": pillar, "image_kind": image_kind,
            "sample_count": sample_count, "mode": "aggregate" if sample_count >= minimum_samples else "descriptive_only",
            "metrics": metrics, "manual_delivery_ids": manual_ids,
            "manual_label": "đăng tay" if manual_ids else None,
        }
        if channel_id.startswith("fb_"):
            section["internal_engagement_rate"] = _legacy_facebook_engagement_rate(
                channel_id, delivery_ids, latest, metric_registry
            )
        sections.append(section)
        title = f"## {channel_id} · {pillar} · {image_kind} ({sample_count} bài)"
        if manual_ids:
            title += " — đăng tay"
        markdown.append(title)
        markdown.append("")
        if not metrics:
            markdown.append("Chưa có metric đã xác minh.")
        else:
            for metric_row in metrics:
                value = f"average={metric_row['average']}" if "average" in metric_row else f"values={metric_row.get('values', [])}; states={metric_row['states']}"
                markdown.append(f"- {metric_row['metric']}: {value}")
        engagement = section.get("internal_engagement_rate")
        if isinstance(engagement, dict):
            if engagement.get("state") == "VALUE":
                markdown.append(
                    f"- internal_engagement_rate: average={engagement['average']}; samples={engagement['samples']}"
                )
            else:
                markdown.append(f"- internal_engagement_rate: UNAVAILABLE ({engagement.get('reason')})")
        markdown.append("")
    if not sections:
        markdown.extend(["Chưa có metric observations.", ""])
    output_dir = root / "insights"
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / f"weekly-{current.date().isoformat()}.md"
    markdown_path.write_text("\n".join(markdown), encoding="utf-8")
    _write_json(output_dir / f"weekly-{current.date().isoformat()}.json", {"generated_at": current.isoformat(), "groups": sections})
    if send_telegram and telegram_notifier is not None and telegram_chat_id:
        try:
            response = telegram_notifier.send(chat_id=telegram_chat_id, text="\n".join(markdown)[:4000])
        except Exception:
            raise ValueError("Telegram report delivery failed") from None
        if not response.get("ok", True):
            raise ValueError("Telegram report delivery failed")
    return markdown_path


def _legacy_facebook_engagement_rate(
    channel_id: str,
    delivery_ids: Sequence[str],
    latest: Mapping[tuple[str, str], tuple[Any, ...]],
    registry: Mapping[str, Any],
) -> dict[str, Any]:
    if capability_state(registry, "facebook_engagement", channel_id) != "SUPPORTED":
        return {"state": "UNAVAILABLE", "reason": "CAPABILITY_BLOCKED", "samples": 0, "average": None}
    rates: list[float] = []
    required = ("post_total_media_view_unique", "reactions_total", "comments_total", "shares")
    for delivery_id in delivery_ids:
        rows = [latest.get((delivery_id, metric)) for metric in required]
        if any(row is None or row[4] not in {"VALUE", "ZERO"} or row[3] is None for row in rows):
            continue
        denominator = rows[0][3]
        if type(denominator) is not int or denominator <= 0:
            continue
        interactions = sum(int(row[3]) for row in rows[1:])
        rates.append(interactions / denominator)
    if not rates:
        return {"state": "UNAVAILABLE", "reason": "DATA_INCOMPLETE", "samples": 0, "average": None}
    return {"state": "VALUE", "reason": None, "samples": len(rates), "average": round(mean(rates), 6)}
