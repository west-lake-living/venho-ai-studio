from __future__ import annotations

from pathlib import Path

import yaml

from growth_engine.adapters.outbound.meta.metric_registry import load_metric_specs


def test_registry_defaults_facebook_engagement_to_blocked() -> None:
    path = Path("config/projects/venho_hotel/growth_engine/metrics_registry.yaml")

    specs = load_metric_specs(path, "fb_hanoi")

    by_name = {spec.name: spec for spec in specs}
    assert set(by_name) == {
        "post_media_view", "post_total_media_view_unique", "reactions_total", "comments_total", "shares"
    }
    assert by_name["reactions_total"].capability_state == "BLOCKED"
    assert by_name["comments_total"].capability_state == "BLOCKED"
    assert by_name["shares"].missing_value_state == "ZERO"


def test_registry_can_enable_engagement_per_page(tmp_path: Path) -> None:
    payload = {
        "capabilities": {
            "facebook_engagement": {
                "default": "BLOCKED",
                "channels": {"fb_hanoi": "SUPPORTED"},
            }
        },
        "metrics": [
            {
                "name": "reactions_total",
                "provider_field": "reactions.summary(total_count).limit(0)",
                "scope": "post_field",
                "period": None,
                "capability": "facebook_engagement",
                "availability": "CONDITIONAL",
                "channels": ["fb_hanoi", "fb_venho"],
            }
        ],
    }
    path = tmp_path / "metrics_registry.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    hanoi = load_metric_specs(path, "fb_hanoi")
    venho = load_metric_specs(path, "fb_venho")

    assert hanoi[0].capability_state == "SUPPORTED"
    assert venho[0].capability_state == "BLOCKED"
