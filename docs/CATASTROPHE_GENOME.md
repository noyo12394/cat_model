# Catastrophe Genome Lab

## Purpose

The Catastrophe Genome Lab is an **experimental, map-adjacent navigation
surface** in RiskChain. It makes two different kinds of event metadata easier
to explore:

1. **Live official events** already returned by the GDACS MHEWS integration.
2. A deliberately small, **source-linked historical catalogue** of 30
   documented catastrophes.

It is not a hazard model, event set, catastrophe model, fragility library,
loss model, severity ranking, or forecast. It must not be used to infer event
extent, likelihood, damage, insured loss, or a real-world event analogue.

The 3D atlas includes generalized Natural Earth 110m country boundaries through
the `world-atlas` package. Those lines are cartographic context only—not event
boundaries, an administrative exposure layer, or an analysis result.

The interaction takes inspiration from immersive geographic radio interfaces:
users orbit a globe, select a beacon, and inspect a compact contextual
surface. RiskChain uses that interaction for catastrophe metadata only; it
does not reuse another product's code, brand, artwork, or audio.

## Inputs and labels

### Live atlas

Live beacons are the exact `GlobalEvent` records already retrieved from GDACS.
Their position is the returned `center` coordinate. Selecting one returns the
user to the standard Live workspace and opens the existing official-event
card. The normal source, timestamp, alert-level, and official-report link stay
visible there.

The live atlas is intentionally limited to records that have a usable centre
coordinate. A beacon means **reported event centre, not impact footprint**.
It has no relationship to a map polygon, flood-depth raster, wind field,
ShakeMap, fire perimeter, population, or financial output.

### Historical catalogue

The historical catalogue contains 30 editorially selected events across
earthquake, cyclone, flood, wildfire, and volcano classes. Every record stores:

- name, date label, country, and one atlas reference coordinate;
- one source-archive family and direct archive URL;
- categorical setting, onset, driver, and secondary-hazard context;
- a coordinate-specific warning.

The reference coordinate is a navigation anchor. It is explicitly **not** an
epicentral rupture, observed impact boundary, inundation extent, cyclone track,
wind field, fire perimeter, burn severity layer, ashfall contour, or loss
footprint.

Archive families currently link to USGS significant-earthquake resources, NOAA
National Hurricane Center/NCEI resources, USGS Volcano Hazards, and the U.S.
National Interagency Fire Center. A source-family URL is a starting point for
review, not a claim that every source page contains a bespoke data record for
every item.

## Metadata helix

The helix is a visual encoding of a binary, categorical 30-trait vector. It is
not biological DNA. Each trait has a visible index and label in the UI.

| Group | Traits |
| --- | --- |
| Hazard | Earthquake, tropical cyclone, flood, wildfire, volcano |
| Era | Before 2000, 2000–2009, 2010–2019, 2020 onward |
| Setting | Coastal, inland, island, mountain |
| Onset | Rapid, multi-day, seasonal/prolonged |
| Primary driver | Ground motion, wind, water, thermal/fire, ash/volcanic material |
| Secondary context | Tsunami, surge, landslide, smoke, lahar, multiple secondary contexts |
| Archive family | USGS, NOAA, other official archive |

`1` means the categorical trait is encoded for the selected catalogue record;
`0` means it is not encoded. Neither state represents magnitude, probability,
severity, duration, exposure, vulnerability, or loss.

## Comparison calculation

The Compare view uses a plain Euclidean distance over the 30 binary values:

```text
d(a, b) = sqrt(sum_i (a_i - b_i)^2)
```

The UI also shows a navigation resemblance percentage:

```text
100 × (1 - d / sqrt(30))
```

Nearest neighbours are the three catalogue records with the lowest distance;
an outlier value is the mean of those three distances. This is deterministic
client-side catalogue navigation. It does not train a model, estimate
probability, calibrate vulnerability, infer causal mechanism, or predict the
next event.

## Implementation

The feature is entirely frontend and additive:

- `apps/web/src/riskchain/genome/genomeData.ts` — typed 30-record catalogue,
  the 30 traits, deterministic vector functions and provenance wording.
- `apps/web/src/riskchain/genome/CatastropheGlobe.tsx` — Three.js/
  React Three Fiber globe, Natural Earth country outlines, graticule, orbit
  controls and clickable beacons.
- `apps/web/src/riskchain/genome/CatastropheGenomeLab.tsx` — Atlas, metadata
  helix, compare and catalogue views.
- `apps/web/src/riskchain/RiskChainWorkspace.tsx` — the `Genome Lab` route.

The only new browser-side dependencies are `three`, `@react-three/fiber`,
`@react-three/drei`, `world-atlas`, and `topojson-client`. The backend
calculation chain, result schemas, fragility curves, source adapters,
model-auditor behaviour and live-event schema remain unchanged.

## Governance and future work

Any future link from this Lab to a hazard footprint, exposure snapshot,
observation, event set, catastrophe calculation, or report must require:

1. source and licence review;
2. a documented spatial and temporal resolution;
3. a model/adapter version;
4. a reproducible manifest; and
5. an explicit UI label for observed, modelled, inferred, demo, or unavailable.

No historical record may be promoted to a calibration dataset or used to
generate fragility curves without a separately approved data and model-review
workflow.
