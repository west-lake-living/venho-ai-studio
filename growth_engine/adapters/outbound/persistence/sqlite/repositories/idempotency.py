from __future__ import annotations

from dataclasses import dataclass

from ._base import SqliteRepository, canonical_json, parse_json


@dataclass(frozen=True)
class IdempotencyResult:
    kind: str
    response_status: int | None = None
    response_json: str | None = None


class IdempotencyReservationLost(RuntimeError):
    pass


class IdempotencyRepository(SqliteRepository):
    def get_or_reserve(
        self,
        principal_id: str,
        endpoint: str,
        key: str,
        request_hash: str,
        *,
        now_ms: int,
        expires_at_ms: int,
    ) -> IdempotencyResult:
        if not self.connection.in_transaction:
            raise RuntimeError("idempotency reservation requires an active transaction")
        if not principal_id.strip() or not endpoint.strip() or not key.strip():
            raise ValueError("idempotency principal, endpoint, and key are required")
        _validate_hash(request_hash)
        if type(now_ms) is not int or type(expires_at_ms) is not int or expires_at_ms <= now_ms:
            raise ValueError("idempotency expiry must be after now")

        identity = (principal_id, endpoint, key)
        row = self.connection.execute(
            """SELECT request_hash, response_status, response_json, expires_at
               FROM api_idempotency WHERE principal_id=? AND endpoint=? AND key=?""",
            identity,
        ).fetchone()
        if row is not None and row["expires_at"] <= now_ms:
            self.connection.execute(
                "DELETE FROM api_idempotency WHERE principal_id=? AND endpoint=? AND key=?",
                identity,
            )
            row = None
        if row is not None:
            if row["request_hash"] != request_hash:
                return IdempotencyResult(kind="MISMATCH")
            return IdempotencyResult(
                kind="REPLAY",
                response_status=row["response_status"],
                response_json=row["response_json"],
            )

        self.connection.execute(
            """INSERT INTO api_idempotency
               (principal_id, endpoint, key, request_hash, response_status, response_json, expires_at)
               VALUES (?, ?, ?, ?, 0, 'null', ?)""",
            (*identity, request_hash, expires_at_ms),
        )
        return IdempotencyResult(kind="NEW")

    def save_response(
        self,
        principal_id: str,
        endpoint: str,
        key: str,
        *,
        request_hash: str,
        response_status: int,
        response_json: str,
    ) -> None:
        if not self.connection.in_transaction:
            raise RuntimeError("idempotency response requires an active transaction")
        _validate_hash(request_hash)
        if type(response_status) is not int or not 100 <= response_status <= 599:
            raise ValueError("response_status must be an HTTP status code")
        canonical_response = canonical_json(parse_json(response_json))
        cursor = self.connection.execute(
            """UPDATE api_idempotency SET response_status=?, response_json=?
               WHERE principal_id=? AND endpoint=? AND key=? AND request_hash=?""",
            (response_status, canonical_response, principal_id, endpoint, key, request_hash),
        )
        if cursor.rowcount != 1:
            raise IdempotencyReservationLost("request hash has no matching idempotency reservation")


def _validate_hash(value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdefABCDEF" for character in value):
        raise ValueError("request_hash must be a 64-character SHA-256 hex digest")
