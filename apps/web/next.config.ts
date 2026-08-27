import type { NextConfig } from "next";

const configuredApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "");

if (process.env.VERCEL && !configuredApiBaseUrl) {
  throw new Error("NEXT_PUBLIC_API_BASE_URL is required for Vercel deployments");
}

const apiBaseUrl = configuredApiBaseUrl ?? "http://localhost:8000/api/v1";

if (!/^https?:\/\//.test(apiBaseUrl) || (process.env.VERCEL && !apiBaseUrl.startsWith("https://"))) {
  throw new Error("NEXT_PUBLIC_API_BASE_URL must be an absolute HTTPS URL in Vercel");
}

const nextConfig: NextConfig = {
  // Standalone output keeps the production Docker image small (section 34
  // local-dev-simple / cloud-deploy requirement) by tracing only the files
  // actually needed at runtime.
  output: "standalone",
  // This repository is deployed with apps/web as Vercel's project root.
  // Pinning it avoids an unrelated lockfile in a parent directory making
  // Turbopack scan the user's entire home directory during local builds.
  turbopack: { root: process.cwd() },
  // Keep the long-running wildfire perimeter action same-origin in the
  // browser. This avoids a cross-origin preflight becoming a teaching-session
  // failure while still forwarding the request to the separately deployed API.
  async rewrites() {
    return [{ source: "/api-proxy/cat/analyses", destination: `${apiBaseUrl}/cat/analyses` }];
  },
};

export default nextConfig;
