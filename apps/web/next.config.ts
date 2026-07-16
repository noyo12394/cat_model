import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output keeps the production Docker image small (section 34
  // local-dev-simple / cloud-deploy requirement) by tracing only the files
  // actually needed at runtime.
  output: "standalone",
};

export default nextConfig;
