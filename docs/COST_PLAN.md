# Cost plan

## Mapping and places (Google Maps Platform, optional)

- The product defaults to MapLibre + OpenStreetMap, which has **zero** Google Maps
  Platform cost, so cost is opt-in, not incurred by default.
- When `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` is set: restrict the key by HTTP referrer in
  the Google Cloud console to your deployed domain(s) only.
- When `GOOGLE_MAPS_SERVER_API_KEY` is set (for Routes/Places proxying): restrict by
  server IP, and route all such calls through the backend (`adapters/google_maps.py`)
  so the browser never issues billed calls directly.
- Recommended before enabling either key in production: set a daily budget + billing
  alert in the Google Cloud console, and cache Places/Routes responses server-side
  (not yet implemented - see `KNOWN_LIMITATIONS.md`).
- The search bar already debounces input (250ms, `TopSearchBar.tsx`) before calling
  `/places/search`, which limits request volume even once that endpoint is backed by a
  real Places Autocomplete call.
- 3D/Photorealistic Tiles are not requested anywhere in this build (2D only), avoiding
  their materially higher per-load cost.

## Other external APIs

- NWS, USGS Water, USGS Earthquakes, and OpenFEMA are free, unauthenticated,
  public-domain APIs with no meaningful cost exposure.
- NASA FIRMS and AirNow require free registered keys; both have documented rate limits
  in their respective docs (see `DATA_SOURCE_CARDS.md` links) - the adapters here
  already fail safe (fall back to demo/unavailable) rather than retrying aggressively
  on a 429.

## Cloud infrastructure (planned, not yet deployed)

Compute is the dominant cost driver at this stage:

- **Cloud Run** (API + web): scale-to-zero configuration keeps idle cost near zero for
  a demo deployment; set max-instance caps to bound worst-case cost.
- **Cloud SQL / PostGIS**: the smallest available tier is more than sufficient for the
  current seeded-data volume; this is not yet provisioned (see `ARCHITECTURE.md`).
- **BigQuery**: not used yet - would only be introduced once large-scale historical
  replay/analysis (section 34) is built.

## Feature flags for expensive services (planned)

Recommended flags for a production rollout, not yet implemented as toggles:
`ENABLE_GOOGLE_MAPS`, `ENABLE_3D_TILES`, `ENABLE_FIRMS`, `ENABLE_AIRNOW` - each gating
a real external call so cost-sensitive deployments can disable specific integrations
without a code change.
