from identity_restoration.infrastructure.persistence.production_release_state import (
    ProductionReleaseState,
    load_production_release_state,
    write_production_release_state,
)


def test_release_state_is_restart_safe_and_only_human_candidate_release_activates(tmp_path) -> None:
    path = tmp_path / "production_release.json"
    state = ProductionReleaseState(
        active_production_version="candidate-v3", active_production_route="candidate-v3",
        feature_flag_state="ON", release_id="r1", promotion_authority="HUMAN",
        promotion_timestamp="2026-09-02T10:15:00Z", rollback_target="comfyui-local",
    )
    write_production_release_state(path, state)

    restored = load_production_release_state(path)
    assert restored == state
    assert restored.candidate_v3_active is True


def test_missing_or_invalid_release_state_fails_closed_to_mock(tmp_path) -> None:
    missing = tmp_path / "missing.json"
    assert load_production_release_state(missing).active_production_route == "mock"
    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"feature_flag_state":"ON","active_production_route":"candidate-v3"}')
    assert load_production_release_state(invalid).active_production_route == "mock"
