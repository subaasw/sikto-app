import type { NextConfig } from 'next';

const BACKEND = process.env.API_INTERNAL_URL ?? 'http://localhost:8000';

const nextConfig: NextConfig = {
  transpilePackages: ['@sikto/scene-kit'],

  async rewrites() {
    return [{ source: '/api/:path*', destination: `${BACKEND}/:path*` }];
  },
};

export default nextConfig;
