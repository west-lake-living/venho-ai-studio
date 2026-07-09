from __future__ import annotations

import calendar
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

from content_studio.content_context import load_content_config


@dataclass
class CalendarResult:
    entries: List[Dict[str, Any]]
    json_path: Path
    markdown_path: Path


def _topics(config: Dict[str, Any]) -> List[Dict[str, str]]:
    topics: List[Dict[str, str]] = []
    for pillar in config.get("content_pillars", {}).get("pillars", []):
        for topic in pillar.get("topics", []):
            topics.append({"pillar": pillar.get("name", pillar.get("id", "pillar")), "topic": topic})
    return topics or [{"pillar": "General", "topic": "Morning at West Lake"}]


def build_calendar(
    project: str,
    month: str,
    *,
    config_root: Path = Path("config/projects"),
    data_root: Path = Path("data/projects"),
) -> CalendarResult:
    year, month_number = [int(part) for part in month.split("-", 1)]
    config = load_content_config(project, config_root=config_root)
    cadence = config.get("calendar_rules", {}).get("cadence", {"facebook": 3})
    topics = _topics(config)
    days_in_month = calendar.monthrange(year, month_number)[1]

    entries: List[Dict[str, Any]] = []
    topic_index = 0
    for channel, posts_per_week in cadence.items():
        total = int(posts_per_week) * 4
        step = max(1, days_in_month // max(1, total))
        day = 1
        for _ in range(total):
            topic = topics[topic_index % len(topics)]
            topic_index += 1
            entries.append(
                {
                    "date": date(year, month_number, min(day, days_in_month)).isoformat(),
                    "channel": channel,
                    "topic": topic["topic"],
                    "pillar": topic["pillar"],
                    "format": "post",
                    "status": config.get("calendar_rules", {}).get("default_status", "planned"),
                    "required_asset": config.get("calendar_rules", {}).get(
                        "required_asset_policy", "existing_asset_or_image_prompt"
                    ),
                    "cta": "booking_soft",
                }
            )
            day += step

    out_dir = data_root / project / "content" / "calendar"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{month}_calendar.json"
    markdown_path = out_dir / f"{month}_calendar.md"
    json_path.write_text(json.dumps({"project": project, "month": month, "entries": entries}, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_lines = [f"# CONTENT CALENDAR {month}", ""]
    markdown_lines.extend(
        f"- {entry['date']} | {entry['channel']} | {entry['pillar']} | {entry['topic']} | {entry['status']}"
        for entry in entries
    )
    markdown_path.write_text("\n".join(markdown_lines), encoding="utf-8")
    return CalendarResult(entries=entries, json_path=json_path, markdown_path=markdown_path)

