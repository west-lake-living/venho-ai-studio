from __future__ import annotations

from analytics_feedback.schemas.feedback_advisory import FeedbackAdvisory


def render_feedback_advisory_md(advisory: FeedbackAdvisory) -> str:
    lines = [
        f"# Feedback Advisory {advisory.advisory_id}",
        "",
        f"Status: {advisory.status}",
        f"Approval required: {advisory.approval_required}",
        "",
        "## Summary",
        advisory.analysis_summary,
        "",
        "## Recommendations",
    ]
    if not advisory.recommendations:
        lines.append("- No strong recommendation.")
    for item in advisory.recommendations:
        lines.append(f"- {item.action} {item.target} ({item.theme}) by {item.modifier}: {item.reason}")
    return "\n".join(lines) + "\n"
