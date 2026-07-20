// Tiny linear-scale helpers for the SVG charts (no chart library needed).

export interface Scale {
  (value: number): number;
  domain: [number, number];
}

export function linearScale(domain: [number, number], range: [number, number]): Scale {
  const [d0, d1] = domain;
  const [r0, r1] = range;
  const span = d1 - d0 || 1;
  const fn = ((value: number) => r0 + ((value - d0) / span) * (r1 - r0)) as Scale;
  fn.domain = domain;
  return fn;
}

export function linePath(points: { x: number; y: number }[], sx: Scale, sy: Scale): string {
  return points.map((p, i) => `${i === 0 ? "M" : "L"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join("");
}

export function areaPath(points: { x: number; y: number }[], sx: Scale, sy: Scale, baselineY: number): string {
  if (points.length === 0) return "";
  const line = linePath(points, sx, sy);
  const last = points[points.length - 1];
  const first = points[0];
  return `${line}L${sx(last.x).toFixed(1)},${baselineY}L${sx(first.x).toFixed(1)},${baselineY}Z`;
}

/** A few round tick values across a domain. */
export function ticks([lo, hi]: [number, number], count = 4): number[] {
  const span = hi - lo || 1;
  const step = span / count;
  return Array.from({ length: count + 1 }, (_, i) => lo + i * step);
}
