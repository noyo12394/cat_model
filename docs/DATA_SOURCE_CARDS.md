# Data source registry & cards

Every source below has a typed adapter in `apps/api/app/adapters/`. Each card lists
what it's used for, what configuration unlocks the live call, and what happens without it.

## National Weather Service (NWS)

- **Used for:** watches/warnings/advisories (Alert records).
- **Adapter:** `adapters/nws.py`. Endpoint: `GET {NWS_BASE_URL}/alerts/active?area=<state>`.
- **Auth:** none required; a descriptive `User-Agent` is sent.
- **License:** U.S. Government work, public domain.
- **Without config / on failure:** falls back to the seeded Bethlehem flash-flood
  warning, labeled `data_status: demo`.

## USGS Water Data

- **Used for:** river/stream gauge height (SensorObservation records).
- **Adapter:** `adapters/usgs_water.py`. Endpoint: `GET {USGS_WATER_BASE_URL}/iv/?format=json&stateCd=<state>&parameterCd=00065`.
- **Auth:** none required.
- **License:** public domain (U.S. Government).
- **Without config / on failure:** falls back to the two seeded demo gauges (Monocacy
  Creek, Lehigh River near Bethlehem).

## USGS Earthquakes

- **Used for:** recent seismic events (HazardEvent records).
- **Adapter:** `adapters/usgs_quake.py`. Endpoint: `{USGS_QUAKE_BASE_URL}/summary/2.5_day.geojson`.
- **Auth:** none required.
- **On failure:** returns an empty list marked `unavailable` - "no significant recent
  earthquake" is a legitimate calm status, not something to fake.

## NASA FIRMS (active fire detections)

- **Used for:** MODIS/VIIRS fire detections.
- **Adapter:** `adapters/firms.py`.
- **Auth:** requires a registered `FIRMS_MAP_KEY` (https://firms.modaps.eosdis.nasa.gov/api/).
- **Status in this build:** the real CSV-parsing call is a documented extension point,
  not yet implemented (no test key available to validate the response shape against).
  Returns `unavailable` with an explanatory note either way.

## AirNow (air quality)

- **Used for:** current AQI (SensorObservation, `sensor_type: air_quality_monitor`).
- **Adapter:** `adapters/airnow.py`.
- **Auth:** requires `AIRNOW_API_KEY` (https://docs.airnowapi.org/).
- **Without config:** returns a demo "moderate AQI" reading matching the Location
  Capsule example in the product spec.

## OpenFEMA

- **Used for:** historical disaster declarations, to eventually ground the Historical
  Analog Finder in real records.
- **Adapter:** `adapters/openfema.py`. Endpoint: `{OPENFEMA_BASE_URL}/v2/DisasterDeclarationsSummaries`.
- **Auth:** none required.
- **Without live reachability:** the Historical Analog Finder uses the seeded, clearly
  labeled synthetic composite analogs instead (see `HistoricalAnalog` records with
  "synthetic composite" in their `why_it_may_not_repeat` field).

## Google Maps Platform

- **Used for:** the map engine (Maps JS API, optionally Street View), and Routes/Places
  proxying if a server key is set.
- **Adapters:** `adapters/google_maps.py` (server-side Routes proxy stub);
  `apps/web/src/components/map/GoogleMapView.tsx` (browser-side map rendering).
- **Auth:** two SEPARATE keys - `GOOGLE_MAPS_SERVER_API_KEY` (backend, IP-restricted,
  for Routes/Places) and `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` (frontend, HTTP-referrer
  restricted, for the map tiles). Never share one key for both purposes.
- **Without config:** the frontend uses MapLibre + OpenStreetMap tiles (no key needed);
  Route Risk uses EarthPulse's own demo route graph over the seeded Bethlehem corridor.

## OpenStreetMap

- **Used for:** default map tiles, and as the license note on facility geometry in the
  seeded demo dataset (approximate coordinates, not surveyed).
- **Auth:** none. Note the tile usage policy (https://operations.osmfoundation.org/policies/tiles/)
  - production deployments should move to a commercial tile provider.
