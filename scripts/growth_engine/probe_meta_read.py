from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml

_REPOSITORY_ROOT = str(Path(__file__).resolve().parents[2])
if _REPOSITORY_ROOT not in sys.path:
    sys.path.insert(0, _REPOSITORY_ROOT)

from shared.meta.graph_client import MetaGraphError, ReadOnlyGraphClient


DEFAULT_CANDIDATES = Path("config/projects/venho_hotel/growth_engine/meta_probe_candidates.yaml")
DEFAULT_CHANNELS = Path("config/projects/venho_hotel/growth_engine/channels.yaml")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only Meta capability probe; values come from the candidate config."
    )
    parser.add_argument("--channel", choices=("fb_hanoi", "fb_venho", "ig_venho"), required=True)
    parser.add_argument("--list-recent", action="store_true", help="List recent posts using the configured edge.")
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--channels", type=Path, default=DEFAULT_CHANNELS)
    return parser


def _redact(value: Any, token: str) -> Any:
    if isinstance(value, str):
        return value.replace(token, "[REDACTED]") if token else value
    if isinstance(value, list):
        return [_redact(item, token) for item in value]
    if isinstance(value, dict):
        return {key: _redact(item, token) for key, item in value.items()}
    return value


def _error_details(error: MetaGraphError) -> dict[str, Any]:
    details: dict[str, Any] = {
        "error_class": error.kind.value if error.kind is not None else "UNCLASSIFIED",
        "http_status": error.status,
    }
    if error.provider_code is not None:
        details["meta_error_code"] = error.provider_code
    if error.provider_subcode is not None:
        details["meta_error_subcode"] = error.provider_subcode
    if error.provider_type is not None:
        details["meta_error_type"] = error.provider_type
    return details


def _load_config(channel_id: str, candidates_path: Path, channels_path: Path) -> tuple[dict[str, Any], str]:
    candidates = yaml.safe_load(candidates_path.read_text(encoding="utf-8")) or {}
    channels = yaml.safe_load(channels_path.read_text(encoding="utf-8")) or {}
    candidate = (candidates.get("channels") or {}).get(channel_id)
    configured_channel = next(
        (row for row in channels.get("channels", []) if row.get("channel_id") == channel_id and row.get("environment") == "production"),
        None,
    )
    if not isinstance(candidate, dict) or not isinstance(configured_channel, dict):
        raise ValueError(f"Meta probe configuration is missing {channel_id}")
    configured_account_id = configured_channel.get("remote_page_id") or configured_channel.get("remote_account_id")
    if str(configured_account_id or "") != str(candidate.get("account_id") or ""):
        raise ValueError(f"candidate account ID does not match channels.yaml for {channel_id}")
    api_version = str(candidate.get("api_version") or candidates.get("api_version") or "")
    if not api_version:
        raise ValueError(f"candidate Graph API version is missing for {channel_id}")
    return candidate, api_version


def _field_probes(client: Any, object_id: str, fields: list[str]) -> list[dict[str, Any]]:
    probes: list[dict[str, Any]] = []
    for field in fields:
        try:
            response = client.get_object(object_id, [field])
            probes.append({"field": field, "result": "READABLE" if field in response else "NOT_RETURNED", "value": response.get(field)})
        except MetaGraphError as error:
            probes.append({"field": field, "result": "ERROR", **_error_details(error)})
    return probes


def _recent_window(days: int) -> tuple[int, int]:
    until_ms = time.time_ns() // 1_000_000
    return until_ms - days * 24 * 60 * 60 * 1000, until_ms


def run_probe(
    args: argparse.Namespace,
    environ: Mapping[str, str],
    *,
    client_factory: Callable[..., Any] = ReadOnlyGraphClient,
) -> dict[str, Any]:
    candidate, api_version = _load_config(args.channel, args.candidates, args.channels)
    token_env = str(candidate.get("token_env") or "")
    token = environ.get(token_env, "").strip()
    if not token:
        raise ValueError(f"required environment variable {token_env} is empty")
    account_id = str(candidate["account_id"])
    fields = [str(value) for value in candidate.get("post_fields", [])]
    if not fields or any(not field.strip() for field in fields):
        raise ValueError(f"candidate post fields are missing for {args.channel}")
    edge = str(candidate.get("collection_edge") or "")
    client = client_factory(api_version=api_version, access_token=token, collection_edge=edge)
    list_recent = bool(args.list_recent or candidate.get("list_recent"))
    result: dict[str, Any] = {
        "channel": args.channel,
        "account_id": account_id,
        "api_version": api_version,
        "candidate_only": True,
        "account_fields": _field_probes(client, account_id, ["id"]),
        "post_fields": [],
        "metrics": [],
    }
    if list_recent:
        since_ms, until_ms = _recent_window(int(candidate.get("recent_days", 7)))
        result["recent_window_ms"] = {"since": since_ms, "until": until_ms}
        try:
            result["recent_posts"] = client.list_recent_posts(
                account_id, since_ms, until_ms, fields, int(candidate.get("max_pages", 3))
            )
        except MetaGraphError as error:
            result["recent_posts"] = {"result": "ERROR", **_error_details(error)}
    else:
        post_id = str(candidate.get("post_id") or "")
        if not post_id:
            raise ValueError(f"candidate sample post ID is missing for {args.channel}")
        result["post_id"] = post_id
        result["post_fields"] = _field_probes(client, post_id, fields)
        for metric in candidate.get("metrics", []):
            name = str(metric.get("name") or "")
            period = metric.get("period")
            try:
                response = client.get_insights(post_id, [name], period)
            except MetaGraphError as error:
                result["metrics"].append(
                    {"metric": name, "period": period, "result": "UNSUPPORTED", **_error_details(error)}
                )
                continue
            result["metrics"].append({"metric": name, "period": period, "result": "READABLE", "response": response})
    return _redact(result, token)


def main() -> int:
    args = _parser().parse_args()
    try:
        result = run_probe(args, dict(os.environ))
    except (OSError, ValueError, MetaGraphError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
