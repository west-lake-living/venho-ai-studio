from __future__ import annotations

from shared.jobs.job_store import JobStore


class Worker:
    def __init__(self, owner: str, store: JobStore | None = None) -> None:
        self.owner = owner
        self.store = store or JobStore()

    def run_once(self, handler) -> bool:
        job = self.store.claim(owner=self.owner)
        if not job:
            return False
        try:
            handler(job["payload"])
        except Exception as exc:
            self.store.fail(job["id"], str(exc))
            return False
        self.store.complete(job["id"])
        return True

    def heartbeat(self, job_id: str, *, lease_seconds: int = 300) -> bool:
        return self.store.heartbeat(job_id, owner=self.owner, lease_seconds=lease_seconds)

    def recover(self) -> int:
        return self.store.recover_expired_leases()
