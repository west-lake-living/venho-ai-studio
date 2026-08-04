from __future__ import annotations

import fcntl
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator


TERMINAL_STATUSES = {"PUBLISHED", "FAILED", "NEEDS_OPERATOR"}


class PublicationRegistry:
    def __init__(self, project: str = "venho_hotel", data_root: Path = Path("data/projects")) -> None:
        self.path = data_root / project / "publishing" / "publication_registry.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_path = self.path.with_suffix(".lock")

    @contextmanager
    def _locked(self) -> Iterator[None]:
        # reserve()/update() are read-modify-write over a flat JSON file; without
        # an exclusive lock two concurrent callers (a retried dispatch and a
        # webhook callback, for example) can both read the same on-disk state
        # and the second writer silently discards the first one's change,
        # defeating the idempotency guarantee this registry exists to provide.
        with self._lock_path.open("w") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"publications": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"publications": []}

    def _save(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def reserve(self, command: dict[str, Any]) -> dict[str, Any]:
        idempotency_key = command["idempotency_key"]
        platform = command["platform"]
        with self._locked():
            data = self.load()
            for item in data["publications"]:
                if item.get("idempotency_key") == idempotency_key and item.get("platform") == platform:
                    return {**item, "duplicate": True}
            publication = {
                "publication_id": command["publication_id"],
                "content_package_id": command["content_package_id"],
                "idempotency_key": idempotency_key,
                "platform": platform,
                "status": "RESERVED",
                "gateway_status": None,
                "platform_post_id": None,
                "permalink": None,
                "reconciliation_proof": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            data["publications"].append(publication)
            self._save(data)
            return publication

    def claim(self, publication_id: str, *, expected_status: str | Iterable[str], claimed_status: str) -> dict[str, Any]:
        """Atomically test-and-set status inside the file lock.

        Guards the approve/reject/edit check-then-act sequence: two concurrent
        callers racing on the same publication_id (double-click, two tabs, a
        client retry after a timeout) must not both observe `expected_status`
        and both proceed to dispatch. Only one claim can win; the loser raises
        immediately instead of silently firing a second real webhook call.

        `expected_status` accepts either one status or a set/list of statuses
        (edit_publication allows editing from either PENDING_APPROVAL or
        GATEWAY_ERROR, for example) -- any status not in the accepted set
        raises the same ValueError as a single-status mismatch.
        """
        accepted = {expected_status} if isinstance(expected_status, str) else set(expected_status)
        with self._locked():
            data = self.load()
            for index, item in enumerate(data["publications"]):
                if item.get("publication_id") == publication_id:
                    if item.get("status") not in accepted:
                        raise ValueError(
                            f"publication_id {publication_id} is not {' or '.join(sorted(accepted))} "
                            f"(status={item.get('status')})"
                        )
                    updated = {**item, "status": claimed_status, "updated_at": datetime.now(timezone.utc).isoformat()}
                    data["publications"][index] = updated
                    self._save(data)
                    return updated
            raise KeyError(f"Unknown publication_id: {publication_id}")

    def update(self, publication_id: str, **changes: Any) -> dict[str, Any]:
        with self._locked():
            data = self.load()
            for index, item in enumerate(data["publications"]):
                if item.get("publication_id") == publication_id:
                    updated = {**item, **changes, "updated_at": datetime.now(timezone.utc).isoformat()}
                    data["publications"][index] = updated
                    self._save(data)
                    return updated
            raise KeyError(f"Unknown publication_id: {publication_id}")

    def find(self, publication_id: str) -> dict[str, Any] | None:
        for item in self.load()["publications"]:
            if item.get("publication_id") == publication_id:
                return item
        return None

    def ensure_publishable_evidence(self, publication_id: str) -> dict[str, Any]:
        publication = self.find(publication_id)
        if publication is None:
            raise KeyError(f"Unknown publication_id: {publication_id}")
        if publication.get("platform_post_id") or publication.get("reconciliation_proof"):
            return publication
        raise ValueError("publication lacks post id or reconciliation proof")
