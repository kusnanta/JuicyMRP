/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  eslint: {
    // ESLint not installed — skip during build
    ignoreDuringBuilds: true,
  },
  typescript: {
    // TypeScript errors caught by IDE/CI separately
    ignoreBuildErrors: false,
  },
}

module.exports = nextConfig
