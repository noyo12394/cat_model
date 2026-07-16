# Database schema

The authoritative schema is `infra/migrations/0001_init.sql` (PostGIS). Key tables:

- `hazard_events`, `alerts`, `forecasts`, `sensor_observations` - normalized records
  from the common data model (section 33), each geometry-indexed (GiST) for
  bounding-box queries.
- `facilities`, `infrastructure_dependencies` - the impact-systems graph (hospitals,
  bridges, fire stations, schools, gauges, and the edges between them) that backs the
  Living Cascade and Route Risk features.
- `incidents`, `incident_timeline_entries`, `incident_fusion_reasons` - the fused,
  evolving events Incident Rooms are built from.
- `historical_analogs` - per-incident analog records.
- `scenarios`, `scenario_results` - reproducible Scenario Lab configurations and their
  computed before/after metrics.
- `user_annotations` - collaboration notes/pins (schema only; no UI yet).
- `portfolios`, `portfolio_assets` - tenant-isolated professional uploads.

**Current runtime status:** the API does not yet read/write this schema - see
"Why an in-memory repository instead of Postgres/PostGIS today" in `ARCHITECTURE.md`.
Applying the migration (`docker-compose up`, or `psql $DATABASE_URL -f
infra/migrations/0001_init.sql`) creates the tables but the running API still serves
from its in-memory demo repository until a Postgres-backed repository implementation
is added behind the same interface.

## Time-series considerations

`sensor_observations` is shaped for a TimescaleDB hypertable (commented-out
`create_hypertable` call in the migration) once real high-frequency gauge/AQI feeds are
ingested continuously - the seeded demo data is far too small a volume to need this
today.
