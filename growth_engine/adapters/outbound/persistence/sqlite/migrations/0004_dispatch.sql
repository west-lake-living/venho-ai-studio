-- 0004_dispatch.sql — outbox, single-gate executions, receipt inbox, verifications
CREATE TABLE outbox_commands (
  id                 TEXT PRIMARY KEY,
  delivery_id        TEXT NOT NULL REFERENCES deliveries(id),
  revision_id        TEXT NOT NULL,
  sequence_no        INTEGER NOT NULL CHECK(sequence_no > 0),
  kind               TEXT NOT NULL CHECK(kind = 'PUBLISH'),
  business_key       TEXT NOT NULL UNIQUE,   -- publish:<delivery>:<revision>:<sequence_no>
  payload_hash       TEXT NOT NULL,
  state              TEXT NOT NULL CHECK(state IN
                       ('PENDING','DELIVERING','ACKED','AUTHORIZED','CANCELLED','EXPIRED')),
  dispatch_epoch     TEXT NOT NULL,
  expires_at         INTEGER NOT NULL,
  next_attempt_at    INTEGER NOT NULL,
  transport_attempts INTEGER NOT NULL DEFAULT 0 CHECK(transport_attempts >= 0),
  acked_at           INTEGER,
  lease_owner        TEXT,
  lease_token        TEXT,
  lease_until        INTEGER,
  last_error         TEXT,
  created_at         INTEGER NOT NULL,
  updated_at         INTEGER NOT NULL,
  FOREIGN KEY(revision_id, delivery_id) REFERENCES delivery_revisions(id, delivery_id),
  FOREIGN KEY(revision_id, payload_hash) REFERENCES delivery_revisions(id, payload_hash),
  UNIQUE(delivery_id, revision_id, sequence_no),
  UNIQUE(id, delivery_id)
);
CREATE UNIQUE INDEX one_open_command_per_delivery ON outbox_commands(delivery_id)
  WHERE state IN ('PENDING','DELIVERING','ACKED');
CREATE INDEX due_outbox ON outbox_commands(state, next_attempt_at, expires_at);

-- Single-gate admission: execution chỉ được tạo tại authorize (không có PREPARING).
CREATE TABLE executions (
  id                TEXT PRIMARY KEY,
  command_id        TEXT NOT NULL UNIQUE,
  delivery_id       TEXT NOT NULL,
  principal_id      TEXT NOT NULL,
  state             TEXT NOT NULL CHECK(state IN ('AUTHORIZED','REPORTED','NO_SIDE_EFFECT','UNKNOWN')),
  grant_id          TEXT NOT NULL UNIQUE,
  authorized_at     INTEGER NOT NULL,
  grant_expires_at  INTEGER NOT NULL CHECK(grant_expires_at > authorized_at),
  receipt_due_at    INTEGER NOT NULL CHECK(receipt_due_at >= grant_expires_at),
  external_outcome  TEXT,
  error_class       TEXT,
  resolved_by       TEXT,
  resolution_reason TEXT,
  updated_at        INTEGER NOT NULL,
  FOREIGN KEY(command_id, delivery_id) REFERENCES outbox_commands(id, delivery_id)
);
-- INV-01 ở mức DB, xuyên mọi command của cùng delivery.
CREATE UNIQUE INDEX one_live_execution_per_delivery ON executions(delivery_id)
  WHERE state IN ('AUTHORIZED','REPORTED','UNKNOWN');
CREATE INDEX execution_receipt_due ON executions(state, receipt_due_at);

-- Không FK tới executions: receipt sai/lạ vẫn phải được lưu làm bằng chứng (QUARANTINED).
CREATE TABLE receipt_inbox (
  id                TEXT PRIMARY KEY,
  issuer_id         TEXT NOT NULL,
  event_id          TEXT NOT NULL,          -- '<grant_id>:<outcome>'
  execution_id      TEXT,                   -- như Make gửi, CHƯA tin
  event_hash        TEXT NOT NULL CHECK(length(event_hash) = 64),
  body_json         TEXT NOT NULL,          -- đã lọc secret
  received_at       INTEGER NOT NULL,
  processing_state  TEXT NOT NULL CHECK(processing_state IN
                      ('RECEIVED','APPLIED','QUARANTINED','IGNORED_STALE')),
  quarantine_reason TEXT,
  applied_at        INTEGER,
  UNIQUE(issuer_id, event_id)
);

CREATE TABLE publication_verifications (
  id            TEXT PRIMARY KEY,
  delivery_id   TEXT NOT NULL REFERENCES deliveries(id),
  execution_id  TEXT REFERENCES executions(id),
  source        TEXT NOT NULL CHECK(source IN ('meta_graph','make_log','manual','legacy')),
  checked_at    INTEGER NOT NULL,
  existence     TEXT NOT NULL CHECK(existence IN ('EXISTS','NOT_FOUND','UNAVAILABLE','ERROR')),
  ownership     TEXT NOT NULL CHECK(ownership IN ('MATCH','MISMATCH','UNAVAILABLE')),
  media_present TEXT NOT NULL CHECK(media_present IN ('YES','NO','UNAVAILABLE')),
  caption_match TEXT NOT NULL CHECK(caption_match IN ('MATCH','MISMATCH','UNAVAILABLE')),
  quality       TEXT NOT NULL CHECK(quality IN ('PASS','WARNING','FAIL','UNAVAILABLE')),
  api_version   TEXT,
  actor_id      TEXT,
  evidence_json TEXT NOT NULL
);
CREATE TRIGGER no_verification_update BEFORE UPDATE ON publication_verifications
BEGIN SELECT RAISE(ABORT, 'verification_is_append_only'); END;
