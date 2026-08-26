from identity_restoration.infrastructure.restorers.comfyui_remote_restorer import ComfyUIRemoteRestorer


def test_v2_candidate_identity_keeps_dimension_preserving_geometry_binding() -> None:
    assert "face_restore_win_sd15_ipadapter_v2_candidate_d30".startswith(
        "face_restore_win_sd15_ipadapter_v2_candidate_"
    )
    # The candidate-prefix branch is intentionally kept beside the production
    # v2 branch; the remote adapter must not drop pad/crop geometry for it.
    assert ComfyUIRemoteRestorer._is_dimension_preserving_workflow(
        "face_restore_win_sd15_ipadapter_v2_candidate_d30"
    )
