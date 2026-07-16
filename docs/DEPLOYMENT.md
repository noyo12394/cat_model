# Deployment

## Local development

See the root `README.md` Quickstart. `docker-compose up --build` runs Postgres/PostGIS,
Redis, the API, a background worker, and the web frontend together.

## Cloud deployment (Google Cloud-oriented, per section 34)

Not yet automated (no Terraform/`gcloud` scripts are included in this build) - this is
the intended target topology:

1. **Cloud Run** for `apps/api` (container from `apps/api/Dockerfile`) and `apps/web`
   (container from `apps/web/Dockerfile`, which already builds a Next.js `standalone`
   output for a small image). Both scale to zero for low-traffic demo deployments.
2. **Cloud SQL for PostgreSQL** with the PostGIS extension enabled, migrated with
   `infra/migrations/0001_init.sql`. Not required to run the current in-memory-backed
   API, but is the persistence target once the repository is swapped (see
   `ARCHITECTURE.md`).
3. **Memorystore (Redis)** for caching, once server-side caching of external API
   responses is implemented (currently the adapters call through on every request -
   acceptable at seeded-data scale, not at production feed volume).
4. **Secret Manager** for every value in `apps/api/.env.example` that isn't a public
   base URL - inject as environment variables into the Cloud Run service, never bake
   into the image.
5. **Cloud Scheduler + Pub/Sub + Cloud Run Jobs** to replace `apps/api/app/worker.py`'s
   simple polling loop with real, scheduled ingestion once live feeds are continuously
   pulled (see `KNOWN_LIMITATIONS.md`).
6. **Cloud Logging / Cloud Monitoring** for the observability described in
   `docs/TEST_PLAN.md`'s load-testing gap and the master prompt's section 42.

## Environment variables at deploy time

- Backend: everything in `apps/api/.env.example`.
- Frontend: `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` are baked
  in at **build** time (Next.js inlines `NEXT_PUBLIC_*` values), so the Docker build
  accepts them as build args (see `apps/web/Dockerfile`) - set them in your CI/CD
  pipeline's build step, not just as a runtime container environment variable.

## What "production-ready" would still require

See `docs/SECURITY.md` ("Designed for, not yet implemented") and
`docs/KNOWN_LIMITATIONS.md` for the concrete list: authentication/RBAC, a real
Postgres-backed repository, signed uploads, and CI-gated dependency scanning are the
highest-priority gaps before a real production rollout.
