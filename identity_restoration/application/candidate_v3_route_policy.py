from __future__ import annotations

import json
from pathlib import Path

from ..domain.policies.candidate_v3_route_policy import (
    CandidateV3RoutePolicy,
    RoutePolicyError,
)


POLICY_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "candidate_v3_route_policy_v1.json"
)


def load_candidate_v3_route_policy(path: Path = POLICY_PATH) -> CandidateV3RoutePolicy:
    """Load the server-owned policy; evaluation remains pure after loading."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RoutePolicyError(f"route policy unavailable or invalid: {path}") from exc
    return CandidateV3RoutePolicy.from_payload(payload)
