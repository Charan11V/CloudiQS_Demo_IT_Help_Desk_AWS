import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  
  async rewrites() {
    // In Docker, proxy to agent-api service
    // In local dev, use NEXT_PUBLIC_API_URL or fallback to localhost:8001
    const apiTarget = process.env.AGENT_API_URL || "http://localhost:8001";
    // Bakery guided helpdesk API (host gateway from Docker web → published :8002)
    const bakeryTarget =
      process.env.BAKERY_API_URL || "http://host.docker.internal:8002";

    return [
      {
        source: "/api-backend/:path*",
        destination: `${apiTarget}/:path*`,
      },
      {
        source: "/bakery-api/:path*",
        destination: `${bakeryTarget}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
