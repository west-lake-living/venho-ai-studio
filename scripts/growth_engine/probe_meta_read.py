from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

_REPOSITORY_ROOT = str(Path(__file__).resolve().parents[2])
if _REPOSITORY_ROOT not in sys.path:
    sys.path.insert(0, _REPOSITORY_ROOT)

from growth_engine.adapters.outbound.meta.graph_client import GraphClient, MetaGraphError


_TOKEN_ENV_BY_CHANNEL = {
    "fb_hanoi": "GE_META_READ_TOKEN_FB_HANOI",
    "fb_venho": "GE_META_READ_TOKEN_FB_VENHO",
    "ig_venho": "GE_META_READ_TOKEN_IG_VENHO",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Probe read-only Meta access for one configured Growth channel."
    )
    parser.add_argument("--channel", choices=tuple(_TOKEN_ENV_BY_CHANNEL), required=True)
    parser.add_argument(
        "--page-id",
        required=True,
        help="Facebook Page ID or Instagram business account ID",
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--post-id")
    target.add_argument(
        "--list-recent",
        action="store_true",
        help="List a bounded window of recent posts instead of probing a supplied post ID.",
    )
    parser.add_argument(
        "--collection-edge",
        help="Verified one-segment collection edge; required with --list-recent.",
    )
    parser.add_argument("--recent-days", type=int, default=7)
    parser.add_argument("--max-pages", type=int, default=3)
    parser.add_argument("--api-version", required=True)
    parser.add_argument(
        "--field",
        action="append",
        dest="fields",
        required=True,
        help="Candidate field from current documentation/config; repeat per field.",
    )
    parser.add_argument(
        "--metric",
        action="append",
        dest="metrics",
        default=[],
        help="Candidate metric from current documentation/config; repeat per metric.",
    )
    parser.add_argument(
        "--period",
        help="Required when probing metrics; value must come from verified config.",
    )
    return parser


def _redact(value: Any, token: str) -> Any:
    if isinstance(value, str):
        return value.replace(token, "[REDACTED]") if token else value
    if isinstance(value, list):
        return [_redact(item, token) for item in value]
    if isinstance(value, dict):
        return {key: _redact(item, token) for key, item in value.items()}
    return value


def _probe_object(client: GraphClient, object_id: str, fields: list[str]) -> list[dict[str, Any]]:
    probes: list[dict[str, Any]] = []
    for field in fields:
        try:
            response = client.get_object(object_id, [field])
            probes.append(
                {
                    "field": field,
                    "result": "READABLE" if field in response else "NOT_RETURNED",
                    "value": response.get(field),
                }
            )
        except MetaGraphError as exc:
            probes.append(
                {
                    "field": field,
                    "result": "ERROR",
                    "error_class": exc.kind.value if exc.kind is not None else "UNCLASSIFIED",
                    "http_status": exc.status,
                }
            )
    return probes


def run_probe(args: argparse.Namespace, environ: dict[str, str]) -> dict[str, Any]:
    if args.metrics and not args.period:
        raise ValueError("--period is required when --metric is used")
    if args.list_recent:
        if args.post_id:
            raise ValueError("--post-id cannot be used with --list-recent")
        if not isinstance(args.collection_edge, str) or not args.collection_edge.strip():
            raise ValueError("--collection-edge is required with --list-recent")
        if type(args.recent_days) is not int or not 1 <= args.recent_days <= 30:
            raise ValueError("--recent-days must be between 1 and 30")
        if type(args.max_pages) is not int or not 1 <= args.max_pages <= 10:
            raise ValueError("--max-pages must be between 1 and 10")
        if args.metrics:
            raise ValueError("metric probes require --post-id")
    elif not args.post_id:
        raise ValueError("--post-id is required unless --list-recent is used")
    token_env = _TOKEN_ENV_BY_CHANNEL[args.channel]
    token = environ.get(token_env, "").strip()
    if not token:
        raise ValueError(f"required environment variable {token_env} is empty")

    # The edge is unused by these object/insights GETs; it is required only by
    # the shared client constructor used for recent-post listing.
    client = GraphClient(
        api_version=args.api_version,
        access_token=token,
        collection_edge=args.collection_edge or "unused_for_object_probe",
    )
    result: dict[str, Any] = {
        "channel": args.channel,
        "account_id": args.page_id,
        "post_id": args.post_id,
        "api_version": args.api_version,
        "account_fields": _probe_object(client, args.page_id, args.fields),
        "post_fields": [] if args.list_recent else _probe_object(client, args.post_id, args.fields),
        "metrics": [],
    }
    if args.list_recent:
        until_ms = time.time_ns() // 1_000_000
        since_ms = until_ms - args.recent_days * 24 * 60 * 60 * 1000
        result["recent_window_ms"] = {"since": since_ms, "until": until_ms}
        try:
            result["recent_posts"] = client.list_recent_posts(
                args.page_id,
                since_ms,
                until_ms,
                args.fields,
                args.max_pages,
            )
        except MetaGraphError as exc:
            result["recent_posts"] = {
                "result": "ERROR",
                "error_class": exc.kind.value if exc.kind is not None else "UNCLASSIFIED",
                "http_status": exc.status,
            }
    for metric in args.metrics:
        try:
            value = client.get_insights(args.post_id, [metric], args.period)
            result["metrics"].append({"metric": metric, "result": "READABLE", "response": value})
        except MetaGraphError as exc:
            result["metrics"].append(
                {
                    "metric": metric,
                    "result": "ERROR",
                    "error_class": exc.kind.value if exc.kind is not None else "UNCLASSIFIED",
                    "http_status": exc.status,
                }
            )
    return _redact(result, token)


def main() -> int:
    args = _parser().parse_args()
    try:
        result = run_probe(args, dict(os.environ))
    except (ValueError, MetaGraphError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
