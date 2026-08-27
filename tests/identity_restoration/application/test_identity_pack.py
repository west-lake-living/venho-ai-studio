from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from identity_restoration.application.identity_pack import (
    IdentityPack,
    IdentityPackMalformedError,
)


def _payload() -> dict:
    return {
        "schemaVersion": "1.0",
        "identityPackId": "test-pack",
        "identitySubjectId": "linh-an",
        "status": "DRAFT",
        "references": [
            {
                "referenceId": "test-reference",
                "artifactPath": "assets/test.png",
                "artifactSha256": "a" * 64,
                "role": "PRIMARY_FRONTAL",
                "pose": {"yawDeg": 0, "pitchDeg": 0, "rollDeg": 0, "toleranceDeg": 10},
                "faceBounds": {"left": 1, "top": 2, "right": 11, "bottom": 12},
                "usableRegions": ["eyes", "nose", "mouth", "jaw", "hairline"],
                "consentOrAuthorityRef": "config/projects/venho_hotel/subjects/linh_an.yaml",
                "approved": True,
            }
        ],
        "sha256": "b" * 64,
    }


def test_identity_pack_and_references_are_immutable() -> None:
    pack = IdentityPack.from_mapping(_payload())

    assert isinstance(pack.references, tuple)
    with pytest.raises(FrozenInstanceError):
        pack.status = "APPROVED"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        pack.references.append(pack.references[0])  # type: ignore[attr-defined]


def test_duplicate_reference_ids_are_rejected_at_application_boundary() -> None:
    payload = _payload()
    payload["references"].append(payload["references"][0].copy())

    with pytest.raises(IdentityPackMalformedError, match="duplicate referenceId"):
        IdentityPack.from_mapping(payload)
