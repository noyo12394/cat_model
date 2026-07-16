-- EarthPulse core schema (section 33 common data model -> PostGIS).
--
-- This is the schema the platform is DESIGNED against - the MVP backend
-- currently runs on an in-memory repository (see apps/api/app/db/) that
-- implements the same shape as these tables so that swapping in a real
-- Postgres/PostGIS-backed repository is a matter of implementing the
-- repository interface against these tables, not a redesign. Applying this
-- migration does not, by itself, change the running API's storage backend.
--
-- Run with: psql "$DATABASE_URL" -f infra/migrations/0001_init.sql
-- (docker-compose applies it automatically via the postgres init hook.)

CREATE EXTENSION IF NOT EXISTS postgis;
-- TimescaleDB is optional and only meaningful once sensor_observations is
-- backed by real, high-frequency feeds. Guarded so this migration still
-- applies on a plain PostGIS instance (e.g. most managed Cloud SQL setups).
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb') THEN
    CREATE EXTENSION IF NOT EXISTS timescaledb;
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS sources (
  source_key         TEXT PRIMARY KEY,
  display_name        TEXT NOT NULL,
  organization         TEXT NOT NULL,
  license              TEXT,
  docs_url             TEXT
);

CREATE TABLE IF NOT EXISTS hazard_events (
  id                    TEXT PRIMARY KEY,
  source_event_id       TEXT,
  source_key            TEXT REFERENCES sources(source_key),
  hazard_type           TEXT NOT NULL,
  status                TEXT NOT NULL,
  headline               TEXT NOT NULL,
  description            TEXT NOT NULL,
  severity               TEXT NOT NULL,
  certainty              TEXT NOT NULL,
  urgency                TEXT NOT NULL,
  observed_at            TIMESTAMPTZ NOT NULL,
  updated_at             TIMESTAMPTZ NOT NULL,
  retrieved_at           TIMESTAMPTZ NOT NULL,
  expires_at             TIMESTAMPTZ,
  geometry               GEOMETRY(GEOMETRY, 4326) NOT NULL,
  measurements           JSONB NOT NULL DEFAULT '{}',
  source_url             TEXT,
  license                TEXT,
  quality_flags          TEXT[] NOT NULL DEFAULT '{}',
  raw_payload_reference  TEXT
);
CREATE INDEX IF NOT EXISTS idx_hazard_events_geometry ON hazard_events USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_hazard_events_observed_at ON hazard_events (observed_at);

CREATE TABLE IF NOT EXISTS alerts (
  id                    TEXT PRIMARY KEY,
  alert_id               TEXT NOT NULL,
  source_key             TEXT REFERENCES sources(source_key),
  hazard_type            TEXT NOT NULL,
  headline                TEXT NOT NULL,
  description             TEXT NOT NULL,
  severity                TEXT NOT NULL,
  certainty               TEXT NOT NULL,
  urgency                 TEXT NOT NULL,
  effective_at            TIMESTAMPTZ NOT NULL,
  expires_at              TIMESTAMPTZ,
  geometry                GEOMETRY(GEOMETRY, 4326) NOT NULL,
  area_description        TEXT,
  retrieved_at            TIMESTAMPTZ NOT NULL,
  data_status             TEXT NOT NULL DEFAULT 'live'
);
CREATE INDEX IF NOT EXISTS idx_alerts_geometry ON alerts USING GIST (geometry);

CREATE TABLE IF NOT EXISTS forecasts (
  id                    TEXT PRIMARY KEY,
  forecast_id            TEXT NOT NULL,
  source_key             TEXT REFERENCES sources(source_key),
  hazard_type            TEXT NOT NULL,
  issued_at              TIMESTAMPTZ NOT NULL,
  valid_from             TIMESTAMPTZ NOT NULL,
  valid_to               TIMESTAMPTZ NOT NULL,
  geometry               GEOMETRY(GEOMETRY, 4326) NOT NULL,
  headline                TEXT NOT NULL,
  detail                  TEXT NOT NULL,
  confidence_note         TEXT
);

CREATE TABLE IF NOT EXISTS sensor_observations (
  id                    TEXT NOT NULL,
  sensor_id              TEXT NOT NULL,
  sensor_name             TEXT NOT NULL,
  sensor_type             TEXT NOT NULL,
  geometry                GEOMETRY(POINT, 4326) NOT NULL,
  observed_at             TIMESTAMPTZ NOT NULL,
  value                   DOUBLE PRECISION NOT NULL,
  unit                    TEXT NOT NULL,
  trend_per_hour          DOUBLE PRECISION,
  is_anomalous            BOOLEAN NOT NULL DEFAULT FALSE,
  anomaly_reason          TEXT,
  source_key              TEXT REFERENCES sources(source_key),
  retrieved_at             TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (id, observed_at)
);
CREATE INDEX IF NOT EXISTS idx_sensor_obs_sensor_time ON sensor_observations (sensor_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_sensor_obs_geometry ON sensor_observations USING GIST (geometry);
-- SELECT create_hypertable('sensor_observations', 'observed_at', if_not_exists => TRUE);  -- when TimescaleDB is present

CREATE TABLE IF NOT EXISTS facilities (
  facility_id            TEXT PRIMARY KEY,
  facility_type          TEXT NOT NULL,
  name                   TEXT NOT NULL,
  geometry               GEOMETRY(GEOMETRY, 4326) NOT NULL,
  operational_state      TEXT NOT NULL DEFAULT 'unknown',
  attributes              JSONB NOT NULL DEFAULT '{}',
  data_completeness       DOUBLE PRECISION NOT NULL DEFAULT 1.0,
  backup_power            BOOLEAN,
  served_population       INTEGER,
  source_key              TEXT REFERENCES sources(source_key)
);
CREATE INDEX IF NOT EXISTS idx_facilities_geometry ON facilities USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_facilities_type ON facilities (facility_type);

CREATE TABLE IF NOT EXISTS infrastructure_dependencies (
  dependency_id          TEXT PRIMARY KEY,
  from_facility_id       TEXT NOT NULL REFERENCES facilities(facility_id),
  to_facility_id         TEXT NOT NULL REFERENCES facilities(facility_id),
  relationship           TEXT NOT NULL,
  strength               DOUBLE PRECISION NOT NULL DEFAULT 0.5,
  is_uncertain           BOOLEAN NOT NULL DEFAULT FALSE,
  source_key             TEXT REFERENCES sources(source_key),
  created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  valid_from              TIMESTAMPTZ,
  valid_to                TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_deps_from ON infrastructure_dependencies (from_facility_id);
CREATE INDEX IF NOT EXISTS idx_deps_to ON infrastructure_dependencies (to_facility_id);

CREATE TABLE IF NOT EXISTS incidents (
  incident_id            TEXT PRIMARY KEY,
  slug                   TEXT UNIQUE NOT NULL,
  title                  TEXT NOT NULL,
  hazard_type            TEXT NOT NULL,
  severity               TEXT NOT NULL,
  status                 TEXT NOT NULL,
  region_label           TEXT NOT NULL,
  center                 GEOMETRY(POINT, 4326) NOT NULL,
  geometry               GEOMETRY(GEOMETRY, 4326),
  description            TEXT NOT NULL,
  created_at             TIMESTAMPTZ NOT NULL,
  updated_at             TIMESTAMPTZ NOT NULL,
  overall_confidence     TEXT NOT NULL,
  one_line_summary       TEXT NOT NULL,
  affected_facility_ids  TEXT[] NOT NULL DEFAULT '{}',
  affected_population_estimate INTEGER,
  sources                TEXT[] NOT NULL DEFAULT '{}',
  is_demo                BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_incidents_center ON incidents USING GIST (center);

CREATE TABLE IF NOT EXISTS incident_timeline_entries (
  entry_id               TEXT PRIMARY KEY,
  incident_id            TEXT NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
  at                     TIMESTAMPTZ NOT NULL,
  label                  TEXT NOT NULL,
  detail                 TEXT NOT NULL,
  certainty_class        TEXT NOT NULL,
  source                 TEXT NOT NULL,
  is_first_detection      BOOLEAN NOT NULL DEFAULT FALSE,
  is_peak                 BOOLEAN NOT NULL DEFAULT FALSE,
  is_recovery             BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_timeline_incident_time ON incident_timeline_entries (incident_id, at);

CREATE TABLE IF NOT EXISTS incident_fusion_reasons (
  incident_id            TEXT PRIMARY KEY REFERENCES incidents(incident_id) ON DELETE CASCADE,
  matched_on             TEXT[] NOT NULL DEFAULT '{}',
  match_confidence       TEXT NOT NULL,
  related_signal_ids     TEXT[] NOT NULL DEFAULT '{}',
  explanation            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historical_analogs (
  analog_id              TEXT PRIMARY KEY,
  incident_id            TEXT REFERENCES incidents(incident_id) ON DELETE CASCADE,
  event_name             TEXT NOT NULL,
  year                   INTEGER NOT NULL,
  similarity_score       DOUBLE PRECISION NOT NULL,
  similarity_features    TEXT[] NOT NULL DEFAULT '{}',
  what_happened_next     TEXT NOT NULL,
  key_differences        TEXT[] NOT NULL DEFAULT '{}',
  why_it_may_not_repeat  TEXT[] NOT NULL DEFAULT '{}',
  data_quality           TEXT NOT NULL,
  source_url             TEXT
);

CREATE TABLE IF NOT EXISTS scenarios (
  scenario_id            TEXT PRIMARY KEY,
  name                   TEXT NOT NULL,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  mode                   TEXT NOT NULL,
  location_label         TEXT NOT NULL,
  center                 GEOMETRY(POINT, 4326) NOT NULL,
  hazard_type            TEXT NOT NULL,
  severity               TEXT NOT NULL,
  duration_hours         DOUBLE PRECISION NOT NULL,
  time_of_day            TEXT NOT NULL,
  river_condition        TEXT,
  advanced_params        JSONB NOT NULL DEFAULT '{}',
  actions                TEXT[] NOT NULL DEFAULT '{}',
  created_by             TEXT
);

CREATE TABLE IF NOT EXISTS scenario_results (
  scenario_id            TEXT PRIMARY KEY REFERENCES scenarios(scenario_id) ON DELETE CASCADE,
  computed_at            TIMESTAMPTZ NOT NULL,
  baseline               JSONB NOT NULL,
  with_actions           JSONB NOT NULL,
  delta                  JSONB NOT NULL,
  assumptions            TEXT[] NOT NULL DEFAULT '{}',
  uncertainty_notes      TEXT[] NOT NULL DEFAULT '{}',
  method                 TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_annotations (
  annotation_id          TEXT PRIMARY KEY,
  incident_id            TEXT REFERENCES incidents(incident_id) ON DELETE CASCADE,
  author                 TEXT NOT NULL,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  text                   TEXT NOT NULL,
  geometry               GEOMETRY(GEOMETRY, 4326)
);

-- Portfolio Mode (section 28): tenant-isolated by portfolio_id + owner_id.
-- A production deployment adds a real tenants/users table and a foreign key
-- + row-level security policy here; this migration establishes the shape.
CREATE TABLE IF NOT EXISTS portfolios (
  portfolio_id           TEXT PRIMARY KEY,
  owner_id               TEXT NOT NULL,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  retention_expires_at   TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS portfolio_assets (
  portfolio_id           TEXT NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
  asset_id               TEXT NOT NULL,
  name                   TEXT,
  geometry               GEOMETRY(POINT, 4326) NOT NULL,
  asset_type             TEXT,
  replacement_value_usd  DOUBLE PRECISION,
  PRIMARY KEY (portfolio_id, asset_id)
);
CREATE INDEX IF NOT EXISTS idx_portfolio_assets_geometry ON portfolio_assets USING GIST (geometry);
