from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from identity_restoration.application.identity_pack import (
    IdentityPackIntegrityError,
    IdentityPackNotApprovedError,
    IdentityPackNotFoundError,
)
from identity_restoration.infrastructure.persistence.file_identity_pack_repository import (
    FileIdentityPackRepository,
    canonical_pack_sha256,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
PACK_ID = "linh-an-production-v3-2026-08"
PACK_FILE = REPO_ROOT / "config/identity_restoration/identity_packs" / f"{PACK_ID}.json"
EXPECTED_A2_SHA256 = "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d"


def _read_payload() -> dict:
    return json.loads(PACK_FILE.read_text(encoding="utf-8"))


def _write_test_repo(tmp_path: Path, payload: dict, *, copy_artifacts: bool = True) -> FileIdentityPackRepository:
    root = tmp_path / "repo"
    pack_directory = root / "config/identity_restoration/identity_packs"
    pack_directory.mkdir(parents=True)
    if copy_artifacts:
        for reference in payload["references"]:
            source = REPO_ROOT / reference["artifactPath"]
            target = root / reference["artifactPath"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    (pack_directory / f"{payload['identityPackId']}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    bounds = {
        reference["artifactPath"]: reference["faceBounds"]
        for reference in payload["references"]
    }

    class FakeDetector:
        def extract(self, path: Path) -> SimpleNamespace:
            face_bounds = bounds[path.relative_to(root).as_posix()]
            return SimpleNamespace(face_bbox=SimpleNamespace(**face_bounds))

    return FileIdentityPackRepository(
        root,
        schema_path=REPO_ROOT / "contracts/identity_restoration/identity_pack_v1.schema.json",
        face_detector=FakeDetector(),
    )


def _recompute_root_hash(payload: dict) -> None:
    payload["sha256"] = canonical_pack_sha256(payload)


def test_valid_approved_pack_loads_with_pinned_detector_and_exactly_one_face() -> None:
    repository = FileIdentityPackRepository(REPO_ROOT)

    pack = repository.get_approved(PACK_ID)

    assert pack.identity_pack_id == PACK_ID
    assert len(pack.references) == 4
    assert len(pack.references_for_role("PRIMARY_FRONTAL")) == 1
    assert len(pack.references_for_role("THREE_QUARTER")) == 1
    assert len(pack.references_for_role("PROFILE")) == 2
    assert pack.references[0].artifact_sha256 == EXPECTED_A2_SHA256
    assert {reference.artifact_path for reference in pack.references} == {
        "assets/linh_an/A2_Front.png",
        "assets/linh_an/identity_pack_v3/B3_Hero_single_face.png",
        "assets/linh_an/identity_pack_v3/C_LeftProfile_single_face.png",
        "assets/linh_an/identity_pack_v3/D_RightProfile_single_face.png",
    }
    assert not any(
        reference.artifact_path.endswith(name)
        for reference in pack.references
        for name in ("B3_Hero.png", "C_LeftProfile.png", "D_RightProfile.png", "linh_an_profile.png")
    )
    assert pack.sha256 == canonical_pack_sha256(_read_payload())


def test_new_reference_hashes_match_actual_bytes() -> None:
    payload = _read_payload()
    for reference in payload["references"][1:]:
        path = REPO_ROOT / reference["artifactPath"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == reference["artifactSha256"]


def test_missing_reference_file_fails_closed(tmp_path: Path) -> None:
    payload = _read_payload()
    repository = _write_test_repo(tmp_path, payload, copy_artifacts=False)
    missing = repository.repo_root / payload["references"][0]["artifactPath"]
    missing.parent.mkdir(parents=True, exist_ok=True)

    with pytest.raises(IdentityPackIntegrityError, match="reference artifact is missing"):
        repository.get(PACK_ID)


def test_modified_reference_bytes_fail_hash_validation(tmp_path: Path) -> None:
    payload = _read_payload()
    repository = _write_test_repo(tmp_path, payload)
    artifact = repository.repo_root / payload["references"][0]["artifactPath"]
    artifact.write_bytes(artifact.read_bytes() + b"modified")

    with pytest.raises(IdentityPackIntegrityError, match="reference artifact sha256 mismatch"):
        repository.get(PACK_ID)


def test_pack_root_hash_mismatch_fails(tmp_path: Path) -> None:
    payload = _read_payload()
    payload["approvedBy"] = "different-actor"
    repository = _write_test_repo(tmp_path, payload)

    with pytest.raises(IdentityPackIntegrityError, match="canonical sha256 mismatch"):
        repository.get(PACK_ID)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda payload: payload["references"].append(copy.deepcopy(payload["references"][0])), "duplicate referenceId"),
        (lambda payload: payload["references"].__setitem__(1, {**payload["references"][1], "role": "PRIMARY_FRONTAL"}), "exactly one PRIMARY_FRONTAL"),
        (lambda payload: [reference.update(role="PROFILE") for reference in payload["references"]], "exactly one PRIMARY_FRONTAL"),
        (lambda payload: payload["references"][0].update(approved=False), "unapproved references"),
    ],
)
def test_approved_pack_structural_invariants_fail_closed(tmp_path: Path, mutation, message: str) -> None:
    payload = _read_payload()
    mutation(payload)
    _recompute_root_hash(payload)
    repository = _write_test_repo(tmp_path, payload)

    with pytest.raises(ValueError, match=message):
        repository.get_approved(PACK_ID)


@pytest.mark.parametrize("status", ["DRAFT", "RETIRED"])
def test_non_approved_pack_cannot_be_returned_by_get_approved(tmp_path: Path, status: str) -> None:
    payload = _read_payload()
    payload["status"] = status
    payload.pop("approvedAt", None)
    payload.pop("approvedBy", None)
    _recompute_root_hash(payload)
    repository = _write_test_repo(tmp_path, payload)

    with pytest.raises(IdentityPackNotApprovedError):
        repository.get_approved(PACK_ID)


def test_unknown_pack_id_fails_explicitly(tmp_path: Path) -> None:
    repository = _write_test_repo(tmp_path, _read_payload())

    with pytest.raises(IdentityPackNotFoundError):
        repository.get("does-not-exist")


def test_pack_id_path_traversal_is_rejected(tmp_path: Path) -> None:
    repository = _write_test_repo(tmp_path, _read_payload())

    with pytest.raises(IdentityPackNotFoundError, match="path traversal"):
        repository.get("../outside")


def test_artifact_path_traversal_is_rejected(tmp_path: Path) -> None:
    payload = _read_payload()
    payload["references"][0]["artifactPath"] = "../outside.png"
    _recompute_root_hash(payload)
    repository = _write_test_repo(tmp_path, payload, copy_artifacts=False)

    with pytest.raises(IdentityPackIntegrityError, match="cannot traverse"):
        repository.get(PACK_ID)


def test_canonical_pack_hash_is_deterministic_and_ignores_root_hash_field() -> None:
    payload = _read_payload()
    reordered = {key: payload[key] for key in reversed(list(payload))}

    assert canonical_pack_sha256(payload) == canonical_pack_sha256(reordered)
