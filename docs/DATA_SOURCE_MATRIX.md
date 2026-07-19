# RiskChain — Data-Source Matrix (Deliverable 6)

Product-level view of the sources the platform uses or is designed to adopt.
This complements the machine-readable registry at `GET /sources/registry`. It is
US-first (section 2.6). **Licences and availability change — verify before any
production or commercial use.** Where a licence needs legal confirmation it is
marked *confirm*.

| Source | Use | Access | Licence | Resolution | Update | Key limitations | Fallback |
|--------|-----|--------|---------|-----------|--------|-----------------|----------|
| Census TIGER/Line | Boundaries, roads | Bulk download / API | US Gov public domain | Block group / line | Annual | No building attributes | Local gov open data |
| ACS 5-year | Population, social exposure | Census API | US Gov public domain | Block group | Annual | Estimates with margins of error | Decennial census |
| FEMA USA Structures | Building footprints | Download / service | US Gov (confirm terms) | Footprint polygon | Periodic | Geometry only; no occupancy/value | MS Buildings / OSM / Overture |
| USGS 3DEP | Terrain / elevation | API / COG | US Gov public domain | 1 m–10 m | Periodic | Not first-floor elevation | Local lidar |
| FEMA NFHL | Regulatory flood zones | Map service | US Gov (confirm terms) | Zone polygons | Periodic | **Zone ≠ depth**; not a loss | Local flood studies |
| USGS Water Data | Streamflow / gauge height | REST API | US Gov public domain | Point gauges | Sub-hourly–daily | Sparse spatial coverage | NOAA water products |
| NOAA/NWS Alerts (CAP) | Official alerts | REST API | US Gov public domain | Zone/polygon | Real-time | Alerts, not measured impact | State/local EM feeds |
| USGS Earthquake / ShakeMap | Seismic hazard/events | REST API / GIS | US Gov public domain | Grid | Real-time | ShakeMap is modelled | Global catalogues |
| NHC advisories / GIS | Hurricane track/wind | Products / GIS | US Gov public domain | Advisory cones | Per advisory | Cone ≠ certainty | HURDAT2 / IBTrACS |
| NASA FIRMS | Active-fire detections | API | NASA (attribution) | 375 m–1 km | Sub-daily | **Hotspots ≠ perimeters** | State fire perimeters |
| OpenFEMA | Declarations, NFIP | REST API | US Gov public domain | County/policy | Periodic | Reporting gaps | NOAA Storm Events |
| OpenStreetMap | Infrastructure geometry | Overpass / extracts | ODbL (share-alike) | Variable | Continuous | Completeness varies | Provider datasets |
| Academic APIs (OpenAlex, Crossref, arXiv, Semantic Scholar) | Method/formula discovery | REST API | Per-source (confirm) | Document | Continuous | Metadata; obey full-text licences | Curated demo index |
| Licensed news API | Live event intelligence (Tier 2) | REST API | Commercial (confirm) | Article | Real-time | Requires licence; dedupe needed | GDELT / publisher RSS |
| X / Reddit / Bluesky | Public-report signals (Tier 3) | Official APIs | Platform terms (confirm) | Post | Real-time | **Signals, not facts**; no scraping | User field reports |
| Google Maps Platform | Basemap / routing | JS + server API | Commercial | — | — | Key restrictions; ToS | MapLibre + self-host tiles |

## Rules carried into the product

- FEMA flood **zones** are never treated as flood **depth** or as a property loss (non-negotiables 8, 9).
- Satellite fire **hotspots** are never drawn as exact fire **perimeters** (section 18.7).
- Social/news content is treated as **signal, not verified measurement**, and never auto-alters a modelled loss (non-negotiables 6, 7).
- Sensitive critical-infrastructure detail is not exposed to unauthorised users (non-negotiable 12); HIFLD is used only with current authorised access.
- Every layer carries provenance and a `data_status`; inferred attributes are shown as inferred (non-negotiables 10, 11).
