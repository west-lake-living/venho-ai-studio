-- 0009_metrics.sql — real analytics (milestone M2, phase P8)
CREATE TABLE metric_observations (
  id               TEXT PRIMARY KEY,
  delivery_id      TEXT NOT NULL REFERENCES deliveries(id),
  metric           TEXT NOT NULL,
  checkpoint       TEXT NOT NULL CHECK(checkpoint IN ('24h','72h','7d','adhoc')),
  observed_at      INTEGER NOT NULL,
  post_age_seconds INTEGER NOT NULL CHECK(post_age_seconds >= 0),
  value            INTEGER,
  value_state      TEXT NOT NULL CHECK(value_state IN ('VALUE','ZERO','NULL','UNAVAILABLE','ERROR')),
  source           TEXT NOT NULL CHECK(source IN ('meta_graph','mock')),
  api_version      TEXT NOT NULL,
  period           TEXT,
  dimensions_json  TEXT NOT NULL DEFAULT '{}',
  error_code       TEXT,
  UNIQUE(delivery_id, metric, checkpoint, observed_at, source),
  CHECK(value_state NOT IN ('VALUE','ZERO') OR value IS NOT NULL),
  CHECK(value_state != 'ZERO' OR value = 0),
  CHECK(value_state IN ('VALUE','ZERO') OR value IS NULL)
);
CREATE TRIGGER no_metric_update BEFORE UPDATE ON metric_observations
BEGIN SELECT RAISE(ABORT, 'metric_observation_is_append_only'); END;
