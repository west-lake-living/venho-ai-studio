-- 0006_research.sql — research/trend candidates owned by Growth editorial decisions
CREATE TABLE research_candidates (
  id              TEXT PRIMARY KEY,
  project_id      TEXT NOT NULL,
  source          TEXT NOT NULL,           -- 'trend_radar' | 'local_intel' | 'guest_voice' | ...
  external_key    TEXT NOT NULL,
  source_revision TEXT NOT NULL,
  event_key       TEXT,
  topic_key       TEXT NOT NULL,
  event_start_at  INTEGER,
  event_end_at    INTEGER,
  expires_at      INTEGER NOT NULL,
  payload_json    TEXT NOT NULL,
  source_hash     TEXT NOT NULL CHECK(length(source_hash) = 64),
  state           TEXT NOT NULL CHECK(state IN ('NEW','APPROVED','REJECTED','USED','EXPIRED')),
  row_version     INTEGER NOT NULL DEFAULT 1 CHECK(row_version > 0),
  created_at      INTEGER NOT NULL,
  UNIQUE(project_id, source, external_key, source_revision)
);
CREATE INDEX candidate_state ON research_candidates(state, expires_at);
CREATE INDEX candidate_event ON research_candidates(event_key);

CREATE TABLE candidate_decisions (
  id           TEXT PRIMARY KEY,
  candidate_id TEXT NOT NULL REFERENCES research_candidates(id),
  source_hash  TEXT NOT NULL CHECK(length(source_hash) = 64),
  decision     TEXT NOT NULL CHECK(decision IN ('APPROVE','REJECT')),
  actor_id     TEXT NOT NULL,
  reason       TEXT,
  created_at   INTEGER NOT NULL
);
CREATE TRIGGER no_candidate_decision_update BEFORE UPDATE ON candidate_decisions
BEGIN SELECT RAISE(ABORT, 'candidate_decision_is_append_only'); END;
