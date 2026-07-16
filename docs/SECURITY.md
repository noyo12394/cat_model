# Security plan

## Implemented in this build

- **Security headers** (`apps/api/app/core/security.py`): `X-Content-Type-Options`,
  `X-Frame-Options: DENY`, `Referrer-Policy`, a restrictive `Content-Security-Policy`.
- **Rate limiting**: an in-memory per-IP token bucket (`RATE_LIMIT_PER_MINUTE`,
  default 120/min). Sufficient for local/dev and a small demo deployment; a
  multi-instance production deployment should move this to an API gateway (Cloud
  Armor, Apigee) and keep this as defense in depth.
- **Input validation**: every request body is a Pydantic model with explicit types and
  `pattern=` constraints on enum-like query params (e.g. `mode`).
- **Upload limits**: portfolio CSV upload is capped at 5 MB and 20,000 rows
  (`apps/api/app/api/v1/portfolio.py`), with per-row validation (coordinates, duplicate
  IDs, non-numeric values) before any data is used.
- **CORS**: explicit allow-list via `CORS_ALLOW_ORIGINS`, not a wildcard.
- **No secrets in the client**: the frontend only ever holds a browser-restricted
  Google Maps key (`NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`); all other credentials
  (`FIRMS_MAP_KEY`, `AIRNOW_API_KEY`, `GOOGLE_MAPS_SERVER_API_KEY`,
  `ANTHROPIC_API_KEY`) live only in backend environment variables and are never
  returned in any API response.
- **Portfolio isolation**: uploaded assets are keyed by a random `portfolio_id` and
  only returned via that id - there is no listing endpoint that enumerates other
  users' portfolios.

## Designed for, not yet implemented

- **Authentication / RBAC**: there is currently no login, no user model, and no
  role-based gating between the public/emergency-management/utility/insurance/research
  user types described in the PRD. Every endpoint is open. Adding this should sit in
  front of the existing routers as FastAPI dependencies (`Depends(get_current_user)`)
  without changing the service layer.
- **Tenant isolation for portfolios**: `infra/migrations/0001_init.sql`'s `portfolios`
  table has an `owner_id` column and is designed for row-level security once auth
  exists; the in-memory repository does not yet enforce ownership checks.
- **Secrets management**: `.env` files are used for local dev. A cloud deployment
  should use Secret Manager (GCP) and inject values as environment variables at
  container start, never baked into the image.
- **Signed upload URLs, virus scanning**: not implemented - the current upload path
  reads the CSV directly into memory. A production deployment handling larger files or
  other formats (GeoJSON/Shapefile/GeoPackage/KML per section 28) should move to
  direct-to-Cloud-Storage signed uploads with a virus-scanning step before processing.
- **Audit logs**: not implemented beyond standard request logging.
- **Dependency scanning**: not wired into CI in this build; recommend `pip-audit` and
  `npm audit` (already run once during setup - see `package-lock.json`) as CI gates.

## Sensitive infrastructure

Facility geometry in the seeded demo dataset uses approximate, publicly-known
locations (a university, hospitals, bridges) - the kind of information already visible
on any public map. This build does not include genuinely sensitive infrastructure
(e.g. exact substation equipment locations), consistent with section 39's instruction
not to publish precise locations of sensitive infrastructure where doing so could
create security risk.
