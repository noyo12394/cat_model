# EarthPulse partner readiness

## What partners can evaluate today

EarthPulse is a presentation-ready decision-support prototype with two clearly
separated surfaces:

| Surface | What it demonstrates | Evidence status |
| --- | --- | --- |
| Global operating picture | Current multi-hazard event metadata, alert level, source freshness, official report links, and a transparent analyst watch queue | Live GDACS API when available |
| Local compound-hazard room | Flood, access, infrastructure, route, consequence and 0–24h horizon interactions | Explicit Lehigh Valley research/demo scenario |

The global map preserves GDACS alert levels, exposes source freshness in UTC,
links to the source report, and can export the normalized records as GeoJSON.
The watch score ranks **verification priority** from the published alert level,
GDACS score and source-update freshness. It is not a hazard probability,
physical forecast or emergency warning.

## Recommended partner walkthrough

1. Open **Global** and click an event on the map.
2. Use the event brief to show the source record, last modification time, watch
   drivers, next verification action and official report.
3. Move the operating horizon. Explain that the global lens changes analyst
   verification priority, while the local map's 0–24h view shows an explicitly
   labelled modeled scenario.
4. Ask the grounded navigator for the selected event's evidence and limits.
5. Return to the local scenario to demonstrate the differentiated value:
   consequence chains, route exposure, uncertainty and possible futures.

## Evidence and authority posture

- GDACS is a UN–European Commission coordination and impact-estimation source;
  its information is indicative and should be cross-checked with national
  authorities.
- EarthPulse does not issue alerts, evacuation orders or safety determinations.
- The local Bethlehem/Lehigh Valley incident, its modelled surfaces and its
  infrastructure graph are research/demo data. The interface labels them as
  such; they must not be presented as current field conditions.
- CAP is the common multi-hazard warning exchange standard. EarthPulse is
  **CAP-aware, not a CAP alerting authority**: it does not create, sign or
  disseminate public CAP messages.

## Required before operational deployment

The following are deliberate delivery gates, not cosmetic backlog items:

1. Jurisdiction-specific authoritative warning agreements and CAP ingestion,
   including source authentication and authority verification.
2. Per-geography model calibration, independent validation, documented
   uncertainty and approval by domain owners before predictive outputs affect
   operations.
3. Identity, role-based access, audit logs, retention policy, incident
   escalation and accessible operator workflows.
4. Feed-monitoring SLOs, caching/degradation policy, regional failover and a
   24/7 operational support model.
5. Security review, penetration test, privacy/data-license review and a
   written human-in-the-loop decision protocol.

## Reference standards and services

- [GDACS overview](https://www.gdacs.org/About/overview.aspx)
- [GDACS MHEWS API quick start](https://www.gdacs.org/Documents/2025/GDACS_API_quickstart_v1.pdf)
- [WMO Common Alerting Protocol](https://public.wmo.int/activities/common-alerting-protocol-cap)
- [OASIS CAP 1.2](https://www.oasis-open.org/standard/cap/)
