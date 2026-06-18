/** @type {import('next').NextConfig} */
const nextConfig = {
  // standalone — компактный self-contained сервер для Docker-образа.
  output: "standalone",
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_BASE_URL:
      process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
  },
};

export default nextConfig;
