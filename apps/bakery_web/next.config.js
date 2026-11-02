/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // In Docker, proxy to bakery-api service
    // Locally, use NEXT_PUBLIC_BAKERY_API_URL or default to localhost:8002
    const apiTarget = process.env.BAKERY_API_URL || 'http://localhost:8002';
    
    return [
      {
        source: '/api/:path*',
        destination: `${apiTarget}/api/:path*`,
      },
    ];
  },
  output: 'standalone',
};

module.exports = nextConfig;
