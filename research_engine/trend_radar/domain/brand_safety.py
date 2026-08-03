from __future__ import annotations


class BrandSafetyGate:
    def __init__(self, policy: dict) -> None:
        self.forbidden = set(policy.get("forbidden_trend_categories", []))
        self.required = set(policy.get("required_intersection", []))

    def evaluate(self, category: str, intersections: list[str]) -> tuple[bool, str]:
        if category in self.forbidden:
            return False, "forbidden_trend_category"
        if self.required and not (set(intersections) & self.required):
            return False, "missing_required_brand_intersection"
        return True, "passed"
