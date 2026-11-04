-- 0002_media_qc.sql — immutable media + QC reports
CREATE TABLE media_assets (
  id              TEXT PRIMARY KEY,
  source_type     TEXT NOT NULL CHECK(source_type IN ('ai_generated','library','upload','fallback','legacy')),
  source_ref      TEXT NOT NULL,
  source_revision TEXT NOT NULL,
  source_sha256   TEXT NOT NULL CHECK(length(source_sha256) = 64),
  original_key    TEXT NOT NULL,
  metadata_json   TEXT NOT NULL,
  created_at      INTEGER NOT NULL,
  UNIQUE(source_type, source_ref, source_revision)
);
CREATE TRIGGER no_asset_update BEFORE UPDATE ON media_assets
BEGIN SELECT RAISE(ABORT, 'media_asset_is_immutable'); END;

CREATE TABLE media_variants (
  id                TEXT PRIMARY KEY,
  asset_id          TEXT NOT NULL REFERENCES media_assets(id),
  transform_version TEXT NOT NULL,
  sha256            TEXT NOT NULL CHECK(length(sha256) = 64),
  object_key        TEXT NOT NULL,
  width             INTEGER NOT NULL CHECK(width > 0),
  height            INTEGER NOT NULL CHECK(height > 0),
  mime              TEXT NOT NULL CHECK(mime = 'image/jpeg'),
  byte_size         INTEGER NOT NULL CHECK(byte_size > 0),
  qc_status         TEXT NOT NULL CHECK(qc_status IN ('PENDING','PASS','FAIL','REVIEW','QUARANTINED')),
  created_at        INTEGER NOT NULL,
  UNIQUE(asset_id, transform_version, sha256)
);
-- Chỉ qc_status được đổi; bytes/identity bất biến.
CREATE TRIGGER variant_bytes_immutable
BEFORE UPDATE OF asset_id, transform_version, sha256, object_key, width, height, mime, byte_size ON media_variants
BEGIN SELECT RAISE(ABORT, 'media_variant_is_immutable'); END;

CREATE TABLE qc_reports (
  id                 TEXT PRIMARY KEY,
  variant_id         TEXT NOT NULL REFERENCES media_variants(id),
  caption_hash       TEXT NOT NULL CHECK(length(caption_hash) = 64),
  ruleset_hash       TEXT NOT NULL CHECK(length(ruleset_hash) = 64),
  fact_snapshot_hash TEXT NOT NULL CHECK(length(fact_snapshot_hash) = 64),
  decision           TEXT NOT NULL CHECK(decision IN ('PASS','FAIL','REVIEW')),
  coverage_gaps_json TEXT NOT NULL DEFAULT '[]',
  result_json        TEXT NOT NULL,
  created_at         INTEGER NOT NULL
);
CREATE TRIGGER no_qc_update BEFORE UPDATE ON qc_reports
BEGIN SELECT RAISE(ABORT, 'qc_report_is_immutable'); END;
CREATE TRIGGER no_qc_delete BEFORE DELETE ON qc_reports
BEGIN SELECT RAISE(ABORT, 'qc_report_is_immutable'); END;
