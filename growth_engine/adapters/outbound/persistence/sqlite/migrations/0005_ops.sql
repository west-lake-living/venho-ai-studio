-- 0005_ops.sql — jobs, audit, incidents, idempotency, budget, legacy import
CREATE TABLE jobs (
  id           TEXT PRIMARY KEY,
  kind         TEXT NOT NULL,
  lane         TEXT NOT NULL CHECK(lane IN ('publish','jobs')),
  business_key TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  state        TEXT NOT NULL CHECK(state IN
                 ('PENDING','RUNNING','SUCCEEDED','FAILED','DEAD','CANCELLED','UNKNOWN')),
  attempts     INTEGER NOT NULL DEFAULT 0 CHECK(attempts >= 0),
  max_attempts INTEGER NOT NULL DEFAULT 3 CHECK(max_attempts > 0),
  run_at       INTEGER NOT NULL,
  lease_owner  TEXT,
  lease_token  TEXT,
  lease_until  INTEGER,
  last_error   TEXT,
  created_at   INTEGER NOT NULL,
  updated_at   INTEGER NOT NULL,
  UNIQUE(kind, business_key)
);
CREATE INDEX jobs_due ON jobs(lane, state, run_at);

CREATE TABLE audit_events (
  id             TEXT PRIMARY KEY,
  aggregate_type TEXT NOT NULL,
  aggregate_id   TEXT NOT NULL,
  actor          TEXT NOT NULL,
  action         TEXT NOT NULL,
  before_hash    TEXT,
  after_hash     TEXT,
  details_json   TEXT NOT NULL DEFAULT '{}',
  correlation_id TEXT NOT NULL,
  created_at     INTEGER NOT NULL
);
CREATE INDEX audit_by_aggregate ON audit_events(aggregate_type, aggregate_id, created_at);
CREATE TRIGGER no_audit_update BEFORE UPDATE ON audit_events
BEGIN SELECT RAISE(ABORT, 'audit_is_append_only'); END;
CREATE TRIGGER no_audit_delete BEFORE DELETE ON audit_events
BEGIN SELECT RAISE(ABORT, 'audit_is_append_only'); END;

CREATE TABLE incidents (
  id               TEXT PRIMARY KEY,
  fingerprint      TEXT NOT NULL,   -- '<type>:<channel_id|->:<delivery_id|dependency>'
  type             TEXT NOT NULL,
  severity         TEXT NOT NULL CHECK(severity IN ('INFO','WARNING','HIGH','CRITICAL')),
  state            TEXT NOT NULL CHECK(state IN ('OPEN','RESOLVED')),
  first_seen_at    INTEGER NOT NULL,
  last_seen_at     INTEGER NOT NULL,
  occurrence_count INTEGER NOT NULL DEFAULT 1 CHECK(occurrence_count > 0),
  details_json     TEXT NOT NULL,
  resolved_at      INTEGER,
  resolved_by      TEXT
);
CREATE UNIQUE INDEX one_open_incident_per_fingerprint ON incidents(fingerprint) WHERE state = 'OPEN';

CREATE TABLE api_idempotency (
  principal_id    TEXT NOT NULL,
  endpoint        TEXT NOT NULL,
  key             TEXT NOT NULL,
  request_hash    TEXT NOT NULL CHECK(length(request_hash) = 64),
  response_status INTEGER NOT NULL,
  response_json   TEXT NOT NULL,
  expires_at      INTEGER NOT NULL,
  PRIMARY KEY(principal_id, endpoint, key)
);

CREATE TABLE paid_calls (
  id              TEXT PRIMARY KEY,
  business_key    TEXT NOT NULL UNIQUE,
  period_key      TEXT NOT NULL,          -- 'YYYY-MM' theo giờ Việt Nam
  currency        TEXT NOT NULL,
  provider        TEXT NOT NULL,
  operation       TEXT NOT NULL,
  state           TEXT NOT NULL CHECK(state IN ('RESERVED','SETTLED','RELEASED','UNKNOWN')),
  reserved_minor  INTEGER NOT NULL CHECK(reserved_minor >= 0),
  actual_minor    INTEGER CHECK(actual_minor IS NULL OR actual_minor >= 0),
  external_job_id TEXT,
  created_at      INTEGER NOT NULL,
  settled_at      INTEGER
);
CREATE INDEX paid_calls_period ON paid_calls(period_key, currency, state);

CREATE TABLE legacy_imports (
  source_name       TEXT NOT NULL,
  source_key        TEXT NOT NULL,
  raw_hash          TEXT NOT NULL CHECK(length(raw_hash) = 64),
  raw_json          TEXT NOT NULL,
  mapped_delivery_id TEXT REFERENCES deliveries(id),
  issue_code        TEXT,
  imported_at       INTEGER NOT NULL,
  PRIMARY KEY(source_name, source_key, raw_hash)
);
