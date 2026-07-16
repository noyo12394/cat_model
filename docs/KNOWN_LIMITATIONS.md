# Known limitations

An honest accounting of what this build does not do, so it's never mistaken for more
than it is.

## Data and region coverage

- Only **one** incident/scenario is seeded (the Bethlehem, PA flood). There is no
  ingestion pipeline continuously creating new incidents from live feeds - Event
  Fusion AI's clustering logic works on any signal set passed to it (see
  `test_event_fusion.py`), but nothing currently feeds it live NWS/USGS data at
  incident-creation time.
- The place directory (`PLACE_DIRECTORY` in `lehigh_valley_flood.py`) is a small,
  hand-written set (~11 places), not a real geocoder. Searching for a place outside
  that set returns no results rather than falling back to a general geocoding API.
- Route Risk only has a real modeled road network for one corridor (Lehigh University
  <-> St. Luke's Bethlehem). Any other origin/destination pair gets a straight-line,
  explicitly low-confidence estimate.
- Facility coordinates in the seeded dataset are approximate, for demonstration -
  not sourced from a surveyed GIS dataset.

## Features from the spec not yet built

- **Model Comparison** (section 24): no side-by-side/swipe/diff UI yet.
- **Budget Optimizer** (section 27): not implemented.
- **Missing-Data Advisor** (section 29): not implemented as its own feature (individual
  facilities do expose a `data_completeness` field that Find Hidden Risks reads).
- **Collaboration** (notes/pins/shared views): `UserAnnotation` schema and DB table
  exist; no UI.
- **Before-and-After imagery view** (section 19) and **Image Understanding AI**
  (section 31.7): not implemented - no imagery pipeline in this build.
- **Evidence Extraction AI** (section 31.6): not implemented - alert text is used
  verbatim rather than NLP-extracted from free-text bulletins.
- **Photorealistic 3D Tiles / 3D Maps**: not requested anywhere (2D only), both to
  control cost by default and because it wasn't required to demonstrate the core flow.
- **Portfolio uploads** only accept CSV in this build, not GeoJSON/Shapefile/
  GeoPackage/KML.
- **Role-based access control**: every endpoint is currently open (see `SECURITY.md`).

## Architecture simplifications

- The API runs on an **in-memory repository**, not the PostGIS schema defined in
  `infra/migrations/0001_init.sql`, even when `docker-compose up` starts a real
  Postgres container alongside it. See `ARCHITECTURE.md` for why, and what changing
  this would involve.
- The "worker" service (`apps/api/app/worker.py`) periodically logs source health as a
  demonstration of the intended background-job pattern; it is not a real scheduled
  ingestion pipeline (no Pub/Sub, no Cloud Scheduler, no persistence of what it finds).
- NASA FIRMS and AirNow adapters do not yet parse a real response (no test credentials
  were available to validate against) - they honestly report `unavailable` rather than
  guessing at a response shape.
- The Grounded AI Assistant is fully rule-based; the `ANTHROPIC_API_KEY`-gated prose
  polish extension point (`_maybe_polish` in `services/assistant.py`) is wired up but
  intentionally left as a no-op pending a real prompt/eval design.

## Mobile UX

The shell is responsive (the intelligence panel moves below the map on narrow
viewports) and was verified at a 390px-wide viewport, but the left navigation rail
does not yet auto-collapse or convert to a bottom nav bar on mobile - it remains a
full-width list, which is usable but not optimized.
