from __future__ import annotations

import argparse
import json
import os
import sys
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
    parser.add_argument("--post-id", required=True)
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
    token_env = _TOKEN_ENV_BY_CHANNEL[args.channel]
    token = environ.get(token_env, "").strip()
    if not token:
        raise ValueError(f"required environment variable {token_env} is empty")

    # The edge is unused by these object/insights GETs; it is required only by
    # the shared client constructor used for recent-post listing.
    client = GraphClient(
        api_version=args.api_version,
        access_token=token,
        collection_edge="unused_for_object_probe",
    )
    result: dict[str, Any] = {
        "channel": args.channel,
        "account_id": args.page_id,
        "post_id": args.post_id,
        "api_version": args.api_version,
        "account_fields": _probe_object(client, args.page_id, args.fields),
        "post_fields": _probe_object(client, args.post_id, args.fields),
        "metrics": [],
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
