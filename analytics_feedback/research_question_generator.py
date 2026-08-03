from __future__ import annotations

from pathlib import Path

from research_engine.adapters.m08_signal_bridge import M08SignalBridge
from shared.security import ensure_safe_slug


def generate_research_question_from_analytics(signal: dict, *, root: Path = Path("research/questions")) -> Path:
    if signal.get("status") == "INCONCLUSIVE":
        question = f"Why is {signal.get('scope', {}).get('pillar', 'this content area')} inconclusive, and what evidence should Ven Ho collect next?"
    elif signal.get("qbsr_drop"):
        question = f"Why did QBSR drop for {signal.get('scope', {}).get('pillar', 'this content area')} despite recent publishing?"
    else:
        question = f"What explains the performance pattern: {signal.get('pattern', 'unknown pattern')}?"
    slug = ensure_safe_slug(f"m08_{signal.get('id', 'strategy_question')}", field="research_question_slug")
    return M08SignalBridge(root=root).add_research_question(slug, question)
