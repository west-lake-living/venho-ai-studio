-- 0001_core.sql — runtime controls, channels, slots, packages
CREATE TABLE runtime_controls (
  environment     TEXT PRIMARY KEY CHECK(environment IN ('test','production')),
  publish_mode    TEXT NOT NULL CHECK(publish_mode IN ('DISABLED','DRY_RUN','LIVE_MANUAL')),
  dispatch_epoch  TEXT NOT NULL,
  global_pause    INTEGER NOT NULL DEFAULT 0 CHECK(global_pause IN (0,1)),
  policy_version  TEXT NOT NULL,
  row_version     INTEGER NOT NULL DEFAULT 1 CHECK(row_version > 0),
  updated_at      INTEGER NOT NULL
);

-- 3 kênh v2: fb_hanoi, fb_venho (Facebook Page), ig_venho (Instagram business account).
CREATE TABLE channels (
  id                TEXT PRIMARY KEY,
  project_id        TEXT NOT NULL,
  environment       TEXT NOT NULL CHECK(environment IN ('test','production')),
  channel_key       TEXT NOT NULL,          -- 'fb_hanoi' | 'fb_venho' | 'ig_venho' (dùng cho filter router Make, tên env)
  platform          TEXT NOT NULL CHECK(platform IN ('facebook','instagram')),
  remote_account_id TEXT NOT NULL,          -- Facebook Page ID hoặc Instagram user ID, luôn TEXT
  name              TEXT NOT NULL,
  enabled           INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)),
  paused            INTEGER NOT NULL DEFAULT 0 CHECK(paused IN (0,1)),
  created_at        INTEGER NOT NULL,
  UNIQUE(environment, platform, remote_account_id),
  UNIQUE(environment, channel_key)
);
CREATE TRIGGER channel_identity_immutable
BEFORE UPDATE OF project_id, environment, channel_key, platform, remote_account_id ON channels
BEGIN SELECT RAISE(ABORT, 'channel_identity_is_immutable'); END;

CREATE TABLE channel_configs (
  id                TEXT PRIMARY KEY,
  channel_id        TEXT NOT NULL REFERENCES channels(id),
  version           INTEGER NOT NULL CHECK(version > 0),
  make_route_ref    TEXT NOT NULL,
  graph_api_version TEXT NOT NULL,
  capability_json   TEXT NOT NULL,
  caption_profile   TEXT NOT NULL DEFAULT 'default',
  config_hash       TEXT NOT NULL CHECK(length(config_hash) = 64),
  created_at        INTEGER NOT NULL,
  UNIQUE(channel_id, version),
  UNIQUE(id, channel_id)
);
CREATE TRIGGER no_channel_config_update BEFORE UPDATE ON channel_configs
BEGIN SELECT RAISE(ABORT, 'channel_config_is_immutable'); END;

CREATE TABLE slots (
  id              TEXT PRIMARY KEY,
  project_id      TEXT NOT NULL,
  local_date      TEXT NOT NULL,
  local_time      TEXT NOT NULL,
  timezone        TEXT NOT NULL,
  lane            TEXT NOT NULL,
  cadence_version TEXT NOT NULL,
  scheduled_at    INTEGER NOT NULL,
  deadline_at     INTEGER NOT NULL CHECK(deadline_at >= scheduled_at),
  cancelled_at    INTEGER,
  cancel_reason   TEXT,
  row_version     INTEGER NOT NULL DEFAULT 1 CHECK(row_version > 0),
  created_at      INTEGER NOT NULL,
  UNIQUE(project_id, local_date, local_time, lane)
);
CREATE INDEX slot_due ON slots(scheduled_at, deadline_at);

CREATE TABLE slot_targets (
  id          TEXT PRIMARY KEY,
  slot_id     TEXT NOT NULL REFERENCES slots(id),
  channel_id  TEXT NOT NULL REFERENCES channels(id),
  required    INTEGER NOT NULL DEFAULT 1 CHECK(required IN (0,1)),
  UNIQUE(slot_id, channel_id),
  UNIQUE(id, channel_id)
);

CREATE TABLE content_packages (
  id                   TEXT PRIMARY KEY,
  slot_id              TEXT NOT NULL REFERENCES slots(id),
  topic_key            TEXT NOT NULL,
  pillar               TEXT NOT NULL,
  lane                 TEXT NOT NULL,
  candidate_id         TEXT,
  source_snapshot_json TEXT NOT NULL,
  fact_snapshot_json   TEXT NOT NULL,
  fact_snapshot_hash   TEXT NOT NULL CHECK(length(fact_snapshot_hash) = 64),
  generation_version   TEXT NOT NULL,
  created_at           INTEGER NOT NULL
);
CREATE INDEX package_topic ON content_packages(topic_key, created_at);
CREATE TRIGGER no_package_update BEFORE UPDATE ON content_packages
BEGIN SELECT RAISE(ABORT, 'content_package_is_immutable'); END;

CREATE TABLE package_facts (
  package_id    TEXT NOT NULL REFERENCES content_packages(id),
  fact_key      TEXT NOT NULL,
  fact_revision TEXT NOT NULL,
  text_hash     TEXT NOT NULL CHECK(length(text_hash) = 64),
  valid_until   INTEGER,
  source_ref    TEXT NOT NULL,
  PRIMARY KEY(package_id, fact_key)
);
