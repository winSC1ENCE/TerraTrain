import type { NextConfig } from "next";

const rawApiUrl =
  process.env.INTERNAL_BACKEND_URL ??
  process.env.BACKEND_URL ??
  "http://backend:8000";
const backendHost = rawApiUrl.replace(/\/api\/v1\/?$/, "").replace(/\/$/, "");

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendHost}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
