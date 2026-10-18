import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // Allow API calls to backend
  async rewrites() {
    return [];
  },
};

export default nextConfig;
