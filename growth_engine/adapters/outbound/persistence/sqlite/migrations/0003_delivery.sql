-- 0003_delivery.sql — deliveries, immutable revisions, append-only approvals
CREATE TABLE deliveries (
  id                   TEXT PRIMARY KEY,
  target_id            TEXT NOT NULL,
  channel_id           TEXT NOT NULL,
  package_id           TEXT NOT NULL REFERENCES content_packages(id),
  current_revision_id  TEXT,
  active_approval_id   TEXT,
  state TEXT NOT NULL CHECK(state IN (
    'DRAFT','IN_REVIEW','APPROVED','QUEUED','EXECUTING',
    'REPORTED_PUBLISHED','PUBLISHED','UNKNOWN','BLOCKED','FAILED_FINAL',
    'EXPIRED','CANCELLED','SUPERSEDED','LEGACY_UNVERIFIED')),
  origin               TEXT NOT NULL DEFAULT 'v2' CHECK(origin IN ('v2','legacy')),
  active               INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
  row_version          INTEGER NOT NULL DEFAULT 1 CHECK(row_version > 0),
  blocked_reason       TEXT,
  platform_post_id     TEXT,
  permalink            TEXT,
  reported_at          INTEGER,
  published_at         INTEGER,
  verified_at          INTEGER,
  verification_quality TEXT CHECK(verification_quality IS NULL OR
                         verification_quality IN ('PASS','WARNING','FAIL','UNAVAILABLE')),
  platform_visibility  TEXT CHECK(platform_visibility IS NULL OR
                         platform_visibility IN ('VISIBLE','DELETED','UNKNOWN')),
  created_at           INTEGER NOT NULL,
  updated_at           INTEGER NOT NULL,
  FOREIGN KEY(target_id, channel_id) REFERENCES slot_targets(id, channel_id),
  FOREIGN KEY(current_revision_id, id)
    REFERENCES delivery_revisions(id, delivery_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY(active_approval_id, current_revision_id)
    REFERENCES approval_decisions(id, revision_id) DEFERRABLE INITIALLY DEFERRED,
  UNIQUE(id, channel_id),
  CHECK(state NOT IN ('APPROVED','QUEUED','EXECUTING') OR
        (current_revision_id IS NOT NULL AND active_approval_id IS NOT NULL)),
  CHECK(state NOT IN ('REPORTED_PUBLISHED','PUBLISHED') OR platform_post_id IS NOT NULL),
  CHECK((state = 'SUPERSEDED') = (active = 0))
);
CREATE UNIQUE INDEX one_active_delivery_per_target ON deliveries(target_id) WHERE active = 1;
CREATE UNIQUE INDEX unique_platform_post_per_page
  ON deliveries(channel_id, platform_post_id) WHERE platform_post_id IS NOT NULL;
CREATE INDEX delivery_state ON deliveries(state, active);

CREATE TABLE delivery_revisions (
  id                TEXT PRIMARY KEY,
  delivery_id       TEXT NOT NULL,
  channel_id        TEXT NOT NULL,
  revision_no       INTEGER NOT NULL CHECK(revision_no > 0),
  channel_config_id TEXT NOT NULL,
  variant_id        TEXT NOT NULL REFERENCES media_variants(id),
  qc_report_id      TEXT NOT NULL REFERENCES qc_reports(id),
  scheduled_at      INTEGER NOT NULL,
  deadline_at       INTEGER NOT NULL CHECK(deadline_at >= scheduled_at),
  caption           TEXT NOT NULL,
  tracking_url      TEXT,
  payload_json      TEXT NOT NULL,
  payload_hash      TEXT NOT NULL CHECK(length(payload_hash) = 64),
  created_by        TEXT NOT NULL,
  created_at        INTEGER NOT NULL,
  FOREIGN KEY(delivery_id, channel_id) REFERENCES deliveries(id, channel_id),
  FOREIGN KEY(channel_config_id, channel_id) REFERENCES channel_configs(id, channel_id),
  UNIQUE(delivery_id, revision_no),
  UNIQUE(id, delivery_id),
  UNIQUE(id, payload_hash)
);
CREATE TRIGGER no_revision_update BEFORE UPDATE ON delivery_revisions
BEGIN SELECT RAISE(ABORT, 'delivery_revision_is_immutable'); END;
CREATE TRIGGER no_revision_delete BEFORE DELETE ON delivery_revisions
BEGIN SELECT RAISE(ABORT, 'delivery_revision_is_immutable'); END;

CREATE TABLE approval_decisions (
  id           TEXT PRIMARY KEY,
  revision_id  TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  decision     TEXT NOT NULL CHECK(decision IN ('APPROVE','REJECT','REVOKE')),
  actor_id     TEXT NOT NULL,
  reason       TEXT,
  revokes_id   TEXT REFERENCES approval_decisions(id),
  created_at   INTEGER NOT NULL,
  FOREIGN KEY(revision_id, payload_hash) REFERENCES delivery_revisions(id, payload_hash),
  UNIQUE(id, revision_id),
  CHECK(decision != 'REVOKE' OR revokes_id IS NOT NULL)
);
CREATE TRIGGER no_approval_update BEFORE UPDATE ON approval_decisions
BEGIN SELECT RAISE(ABORT, 'approval_decision_is_immutable'); END;
CREATE TRIGGER no_approval_delete BEFORE DELETE ON approval_decisions
BEGIN SELECT RAISE(ABORT, 'approval_decision_is_immutable'); END;
