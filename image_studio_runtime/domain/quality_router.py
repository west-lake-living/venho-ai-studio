from __future__ import annotations


def choose_quality(risk_class: str, policy: dict, *, paid: bool = False) -> str:
    image_policy = policy.get("image", {})
    routing = policy.get("quality_routing", {})
    if paid and image_policy.get("paid_default_quality"):
        return image_policy["paid_default_quality"]
    return routing.get(risk_class, policy.get("default_quality", image_policy.get("default_quality", "medium")))


def aggregate_image_verdict(alignment_report: dict, derivative_report: dict, *, alignment_min: float = 0.95) -> str:
    reports = [alignment_report, derivative_report]
    if any(report.get("status") != "completed" for report in reports):
        return "UNVALIDATED"
    if any(report.get("kill_switches") for report in reports):
        return "NEEDS_REVIEW"
    if float(alignment_report.get("alignment_score", 0.0)) < alignment_min:
        return "NEEDS_REVIEW"
    return "APPROVED"
