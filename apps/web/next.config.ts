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
    // Bakery guided helpdesk API (compose service on AWS; host gateway for local bakery compose)
    const bakeryTarget =
      process.env.BAKERY_API_URL || "http://bakery-api:8000";

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
