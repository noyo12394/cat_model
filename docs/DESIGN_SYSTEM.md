# RiskChain — "Catastrophe Terminal" design system

A distinctive visual identity that keeps the existing layout and every
data-honesty label intact. It ships as one drop-in token file:
`apps/web/src/styles/riskchain-tokens.css`.

## Principles
1. **Color is a law, not decoration.** Color only ever encodes *certainty* or
   *severity* — never brand flourish. `observed / modelled / inferred / demo /
   severe` each own a hue; the teal **accent** is reserved for interactive
   affordances only.
2. **Numbers are instruments.** Every figure renders in tabular monospace so a
   loss reads like a financial terminal, not body copy.
3. **Dark is the working surface.** Model & Live default to the dark "terminal"
   theme; Explore & Learn stay light "field". The map is the visual star.
4. **Motion is feedback, never noise.** 160ms transitions; a one-shot shimmer on
   the loss reveal; a pulse only on live events. All disabled under
   `prefers-reduced-motion`.

## Palette
| Token | Hex | Meaning |
|-------|-----|---------|
| `--rc-accent` | `#16d6be` | interactive / focus (teal) |
| `--rc-observed` | `#35c77b` | observed / confirmed |
| `--rc-modelled` | `#4fa8ff` | modelled |
| `--rc-inferred` | `#b48cff` | AI-inferred |
| `--rc-demo` | `#f6a94a` | demo / warning / unavailable |
| `--rc-severe` | `#ff5b55` | severe / conflict |

Dark terminal base `#0b0f14`, panels `#131a21`, hairlines `#223039`.
Light field base `#f4f7f9`, panels `#ffffff`, hairlines `#dbe3e9`.

## Type
- Display / headings: **Space Grotesk** (fallback General Sans → Inter).
- Body: **Inter**.
- Numbers: **IBM Plex Mono** with `font-variant-numeric: tabular-nums`.

Self-host the two extra faces (avoids a CDN/CSP dependency): drop the woff2
files in `apps/web/public/fonts/` and add `@font-face` blocks. Until then the
stacks fall back gracefully to system fonts.

## Adoption (one import, no component rewrites)
In `apps/web/src/app/globals.css`, right after the two `@import` lines:

```css
@import "tailwindcss";
@import "maplibre-gl/dist/maplibre-gl.css";
@import "../styles/riskchain-tokens.css";   /* ← add this */
```

Then delete the file's existing `:root { … }` and
`.riskchain-app.operations { … }` blocks — the token file supplies both, and it
**re-aliases the legacy variable names** (`--bg`, `--surface`, `--text`,
`--line`, `--blue`, `--green`, `--amber`, `--red`, `--purple`, `--shadow`), so
every existing component keeps working unchanged.

To default Model & Live into the dark terminal theme, add the `operations`
class (or `data-rc-theme="terminal"`) when `view === "model" || view === "live"`
in `RiskChainWorkspace.tsx`.

## Utility classes provided
- `.rc-num` — tabular-mono number styling for any figure.
- `.rc-chip--observed|modelled|inferred|demo|severe|neutral` — certainty badges.
- `.rc-elevated`, `.rc-glass`, `.rc-hairline` — surfaces.
- `.rc-reveal` — one-shot loss shimmer (add on run completion).
- `.rc-pulse` — live-event marker pulse.
- `.rc-focusable` — teal focus glow.

## Preview
`apps/web/public/design-preview.html` renders the full palette, type scale, and
sample components in both themes. Once deployed it's viewable at
`/design-preview.html`; it also opens directly from disk.

---

## Prompt to hand Codex (verbatim)

> **Adopt the RiskChain "catastrophe terminal" design system without changing
> any backend, API calls, or certainty/provenance semantics.**
>
> 1. In `apps/web/src/app/globals.css`, add `@import "../styles/riskchain-tokens.css";`
>    after the existing imports and delete the old `:root` and
>    `.riskchain-app.operations` blocks (the token file supplies both and aliases
>    all legacy variable names).
> 2. Default the **dark terminal** theme for Model & Live views and the light
>    **field** theme for Explore & Learn (toggle the existing `operations` class
>    by `view`). Keep the manual light/dark button working.
> 3. Enforce the **color law**: refactor `StatusBadge` and any colored text to use
>    `--rc-observed/modelled/inferred/demo/severe`; color must never be decorative.
> 4. Put **all numeric values** in `.rc-num` (tabular IBM Plex Mono). Self-host
>    Space Grotesk (display) + IBM Plex Mono (numbers) in `public/fonts/` with
>    `@font-face`.
> 5. Add a **count-up + `.rc-reveal` shimmer** to the loss-hero figure on run
>    completion (respect `prefers-reduced-motion`).
> 6. Consolidate the results drawer to **4 tabs — Overview · Curves · Financials ·
>    Audit** — and fix the scenario-builder step numbering (no 1,2,3,6,7 gaps).
>    Make "blocked/unavailable" states calm gray, not alarming amber.
> 7. Keep **WCAG-AA** contrast in both themes; charts must use pattern+label, not
>    color alone; full keyboard nav preserved. Run `tsc`, lint, and `next build`
>    and confirm all three pass.
