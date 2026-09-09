from __future__ import annotations

from pathlib import Path

from research_engine.local_beat.entities import BeatEntity, BeatItem


def write_entity_note(entity: BeatEntity, items: list[BeatItem], *, vault_root: Path = Path("vault")) -> Path:
    path = vault_root / "local_beat" / f"{entity.id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        f"# {entity.name}",
        "",
        f"- Entity: `{entity.id}`",
        f"- Category: `{entity.category}`",
        f"- Guest relevance: `{entity.guest_relevance}`",
        f"- Tracked since: `{entity.tracked_since}`",
        "",
        "| Detected | Status | Title | URL |",
        "|---|---|---|---|",
    ]
    for item in sorted(items, key=lambda value: value.detected_at, reverse=True):
        rows.append(f"| {item.detected_at} | {item.status.value} | {item.title.replace('|', '/')} | [{item.url}]({item.url}) |")
    if not items:
        rows.append("| — | — | Chưa có beat item | — |")
    rows.extend([
        "",
        "> BeatItem là chất liệu bối cảnh. Không dùng số liệu như factual claim nếu chưa có fact R3 active trong M01.",
    ])
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path
