"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { PortfolioExposure } from "@/lib/types";

/** Portfolio Mode (section 28), scoped to CSV upload in this build. */
export function PortfolioPanel() {
  const [result, setResult] = useState<PortfolioExposure | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  async function handleFile(file: File) {
    setUploading(true);
    setError(null);
    try {
      const res = await api.uploadPortfolio(file);
      setResult(res);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-4 p-4">
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground/50">Portfolio</h2>
        <p className="mt-1 text-xs text-foreground/60">
          Upload a CSV of assets (columns: asset_id, name, lat, lon, asset_type, replacement_value_usd) to
          check exposure against the current active alert area. Processed for this session only - never
          exposed publicly.
        </p>
      </div>

      <label className="block">
        <span className="sr-only">Upload portfolio CSV</span>
        <input
          type="file"
          accept=".csv"
          disabled={uploading}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
          className="block w-full text-sm"
        />
      </label>

      {uploading && <p className="text-sm text-foreground/60">Validating and analyzing…</p>}
      {error && <p className="text-sm text-status-severe">{error}</p>}

      {result && (
        <div className="space-y-3 border-t border-border pt-3 text-sm">
          <dl className="grid grid-cols-2 gap-2">
            <div className="rounded-md border border-border p-2">
              <dt className="text-xs text-foreground/50">Valid assets</dt>
              <dd className="text-lg font-semibold">{result.valid_asset_count}</dd>
            </div>
            <div className="rounded-md border border-border p-2">
              <dt className="text-xs text-foreground/50">In active alert</dt>
              <dd className="text-lg font-semibold">{result.assets_in_active_alert}</dd>
            </div>
          </dl>
          <p className="text-foreground/80">{result.accumulation_hotspot_note}</p>
          <p className="text-xs text-foreground/60">
            {result.missing_value_count} asset(s) are missing a replacement value.
          </p>
          {result.validation_issues.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-foreground/50">Validation issues</h3>
              <ul className="mt-1 max-h-40 overflow-y-auto text-xs text-foreground/60">
                {result.validation_issues.map((issue, i) => (
                  <li key={i}>
                    {issue.row_number ? `Row ${issue.row_number}: ` : ""}
                    {issue.issue}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <p className="text-[11px] text-foreground/50">{result.disclaimer}</p>
        </div>
      )}
    </div>
  );
}
