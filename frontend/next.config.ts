import type { NextConfig } from "next";

const backendUrl =
  process.env.INTERNAL_API_URL ?? "http://backend:8000";

const nextConfig: NextConfig = {
  /* config options here */
  webpack: (config, { dev }) => {
    if (dev) {
      config.watchOptions = {
        // イベント監視が不安定な環境向けにポーリングへ
        poll: 1000,            // 1秒ごとに差分チェック
        aggregateTimeout: 200, // 変更連打時に200ms待ってまとめて再ビルド
        // ignored: /node_modules/, // 必要なら監視除外（既定で除外）
      };
    }
    return config;
  },
  turbopack: {},
  output: "standalone",

  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
