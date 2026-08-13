import { createRequire } from 'node:module';
import type { NextConfig } from 'next';

const BACKEND = process.env.API_INTERNAL_URL ?? 'http://localhost:8000';
const require = createRequire(import.meta.url);

const nextConfig: NextConfig = {
  transpilePackages: ['@sikto/scene-kit', '@sikto/motion-kit'],

  webpack: (config) => {
    // motion-kit is transpiled from source, so its `remotion` import would
    // resolve to its own pnpm instance — force the app's single copy or the
    // Player throws a version/context mismatch.
    config.resolve.alias = {
      ...config.resolve.alias,
      remotion$: require.resolve('remotion'),
      'remotion/no-react$': require.resolve('remotion/no-react'),
    };
    return config;
  },

  async rewrites() {
    return [{ source: '/api/:path*', destination: `${BACKEND}/:path*` }];
  },
};

export default nextConfig;
