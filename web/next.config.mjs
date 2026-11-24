/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  eslint: { ignoreDuringBuilds: true },
  // La interfaz no habla directo con la API: lo hace por /api (app/api/[...path]/route.js),
  // así el navegador no necesita CORS y la dirección de la API se configura con API_URL.
};
export default nextConfig;
