from __future__ import annotations

from validator_studio.controlled_matrix import load_controlled_matrix, run_passes_gates, summarize_matrix


def _approved(case_id: str, completed_at: str) -> dict:
    return {
        "case_id": case_id,
        "completed_at": completed_at,
        "verdict": "approved",
        "actor_geometry_ok": True,
        "scores": {
            "face_identity": 91,
            "outfit_match": 92,
            "scenario_location": 93,
            "technical_quality": 88,
        },
    }


def test_controlled_matrix_contract_is_offline_safe() -> None:
    matrix = load_controlled_matrix()

    assert matrix["contract_version"] == "1.0"
    assert matrix["paid_generation_allowed_in_tests"] is False
    assert [case["case_id"] for case in matrix["cases"]] == ["E1", "E2", "E3", "E4", "E5", "E6"]


def test_run_with_missing_validator_never_passes_gate() -> None:
    matrix = load_controlled_matrix()
    run = _approved("E1", "2026-07-16T01:00:00")
    run["unvalidated"] = True

    assert run_passes_gates(run, matrix["acceptance_gates"]) is False


def test_two_consecutive_approved_runs_are_required_per_case() -> None:
    matrix = load_controlled_matrix()
    records = [
        _approved("E1", "2026-07-16T01:00:00"),
        {**_approved("E1", "2026-07-16T02:00:00"), "scores": {"face_identity": 70}},
        _approved("E1", "2026-07-16T03:00:00"),
        _approved("E1", "2026-07-16T04:00:00"),
    ]

    summary = summarize_matrix(records, matrix)
    e1 = next(case for case in summary["cases"] if case["case_id"] == "E1")
    e2 = next(case for case in summary["cases"] if case["case_id"] == "E2")

    assert e1["production_ready"] is True
    assert e2["production_ready"] is False
    assert summary["production_ready"] is False
