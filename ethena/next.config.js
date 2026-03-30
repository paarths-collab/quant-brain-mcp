/** @type {import('next').NextConfig} */
const backendOrigin =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  process.env.BACKEND_URL ||
  'http://127.0.0.1:8001'

const nextConfig = {
  reactStrictMode: false,

  // Proxy all /api/* requests to the FastAPI backend.
  // This eliminates CORS issues in development entirely
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendOrigin}/api/:path*`,
      },
      {
        source: '/ws/:path*',
        destination: `${backendOrigin}/ws/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;