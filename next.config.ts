import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {},
  serverExternalPackages: ["@react-pdf/renderer"],
};

export default nextConfig;
