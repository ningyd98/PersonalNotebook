/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/:path*`,
      },
      {
        source: "/model/:path*",
        destination: `${process.env.NEXT_PUBLIC_MODEL_GATEWAY_URL || "http://localhost:8900"}/model/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
