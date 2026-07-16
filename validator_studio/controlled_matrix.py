from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_MATRIX_PATH = Path("config/quality/controlled_live_matrix.json")


def load_controlled_matrix(path: Path = DEFAULT_MATRIX_PATH) -> dict[str, Any]:
    matrix = json.loads(path.read_text(encoding="utf-8"))
    if matrix.get("contract_version") != "1.0":
        raise ValueError("Unsupported controlled matrix contract_version")
    if matrix.get("paid_generation_allowed_in_tests") is not False:
        raise ValueError("Controlled matrix must not allow paid generation in tests")
    return matrix


def run_passes_gates(run: dict[str, Any], gates: dict[str, Any]) -> bool:
    if run.get("unvalidated") or str(run.get("verdict", "")).lower() != "approved":
        return False
    if gates.get("actor_geometry_required") and run.get("actor_geometry_ok") is not True:
        return False
    scores = run.get("scores", {})
    return (
        float(scores.get("face_identity", 0)) >= gates["face_identity_min"]
        and float(scores.get("outfit_match", 0)) >= gates["outfit_match_min"]
        and float(scores.get("scenario_location", 0)) >= gates["scenario_location_min"]
        and float(scores.get("technical_quality", 0)) >= gates["technical_quality_min"]
    )


def has_required_consecutive_passes(runs: list[dict[str, Any]], gates: dict[str, Any], required: int) -> bool:
    streak = 0
    for run in sorted(runs, key=lambda item: item.get("completed_at", "")):
        streak = streak + 1 if run_passes_gates(run, gates) else 0
        if streak >= required:
            return True
    return False


def summarize_matrix(records: list[dict[str, Any]], matrix: dict[str, Any] | None = None) -> dict[str, Any]:
    matrix = matrix or load_controlled_matrix()
    gates = matrix["acceptance_gates"]
    required = int(matrix["required_consecutive_approved_runs"])
    cases = []
    for case in matrix["cases"]:
        case_runs = [record for record in records if record.get("case_id") == case["case_id"]]
        production_ready = has_required_consecutive_passes(case_runs, gates, required)
        cases.append({
            **case,
            "runs": len(case_runs),
            "production_ready": production_ready,
            "latest_verdict": case_runs[-1].get("verdict") if case_runs else "not_run",
        })
    return {
        "matrix_id": matrix["matrix_id"],
        "production_ready": all(case["production_ready"] for case in cases),
        "cases": cases,
    }
