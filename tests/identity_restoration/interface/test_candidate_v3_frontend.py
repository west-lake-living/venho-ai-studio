from __future__ import annotations

import pytest

from identity_restoration.interface.candidate_v3_frontend import (
    CandidateV3FrontendError,
    build_candidate_v3_ui_state,
    make_client_payload,
    redact_candidate_v3_client_result,
    validate_client_payload,
)


def _result(**overrides):
    result = {
        "jobId": "job-1",
        "runId": "run-1",
        "attemptId": "attempt-1",
        "status": "COMPLETED",
        "route": "ELIGIBLE",
        "qualityStatus": "PASS",
        "preflight": {"status": "PASS", "reasons": []},
        "correctness": {
            "status": "PASS",
            "transformValid": True,
            "geometryValid": True,
            "maskContainmentValid": True,
            "pixelLockPassed": True,
            "lineageValid": True,
            "reasons": [],
        },
        "qualityScopes": {
            "FACE_LOCAL": {"status": "PASS", "scores": {"faceScore": 95.0}, "reasons": []},
            "BOUNDARY": {"status": "PASS", "scores": {}, "reasons": []},
            "SCENARIO_GLOBAL": {"status": "PASS", "scores": {}, "reasons": []},
        },
        "workflowPath": "/private/workflow.json",
        "effectiveConfigSha256": "secret",
    }
    result.update(overrides)
    return result


def test_projection_redacts_paths_and_config_values_and_separates_scopes():
    public = redact_candidate_v3_client_result(_result())
    assert "workflowPath" not in public
    assert "effectiveConfigSha256" not in public
    state = build_candidate_v3_ui_state(public, available_profile_ids=("profile-1",))
    assert set(state["quality"]["scopes"]) == {"FACE_LOCAL", "BOUNDARY", "SCENARIO_GLOBAL"}
    assert state["quality"]["scopes"]["FACE_LOCAL"]["scores"] == {"faceScore": 95.0}
    assert state["profileSelector"]["options"] == [{"profileId": "profile-1"}]


def test_non_pass_cannot_render_approval_and_review_retry_requires_new_attempt():
    state = build_candidate_v3_ui_state(
        _result(status="REVIEW_REQUIRED", qualityStatus="NEEDS_REVIEW", route="REVIEW_REQUIRED"),
        available_profile_ids=("profile-1",),
    )
    assert state["actions"]["approve"] == {"visible": False, "enabled": False}
    assert state["actions"]["retry"]["enabled"] is True
    assert state["actions"]["retry"]["requiresNewAttemptId"] is True
    assert state["actions"]["retry"]["automatic"] is False


def test_base_regeneration_is_explicit_and_never_automatic_retry():
    state = build_candidate_v3_ui_state(
        _result(status="BASE_REGEN_REQUIRED", qualityStatus="UNVALIDATED", route="BASE_REGEN_REQUIRED"),
        available_profile_ids=("profile-1",),
    )
    assert state["baseRegenerationRequired"] is True
    assert state["automaticRetry"] is False
    assert state["actions"]["baseRegeneration"] == {"visible": True, "enabled": True, "automatic": False}
    assert state["actions"]["retry"]["enabled"] is False


def test_missing_scope_evidence_fails_closed_to_unvalidated():
    state = build_candidate_v3_ui_state(
        _result(qualityScopes={"FACE_LOCAL": {"status": "PASS", "scores": {}, "reasons": []}}),
        available_profile_ids=(),
    )
    assert state["quality"]["scopes"]["BOUNDARY"]["status"] == "UNVALIDATED"
    assert state["actions"]["approve"]["visible"] is False


def test_client_payloads_are_ids_only():
    assert make_client_payload("retry", jobId="job-1", attemptId="attempt-2") == {
        "action": "retry",
        "jobId": "job-1",
        "attemptId": "attempt-2",
    }
    with pytest.raises(CandidateV3FrontendError, match="UNSAFE_FIELD"):
        validate_client_payload({"jobId": "job-1", "configPath": "/tmp/config.json"})
    with pytest.raises(CandidateV3FrontendError, match="IDS_ONLY"):
        make_client_payload("retry", jobId="job-1", config="x")
