import type { NextConfig } from "next"

// A generated FORGE site (D-226). Remote images come from the owner's uploads later.
// FORGE_TURBOPACK_ROOT is set only by FORGE's build worker (D-231): each build folder links the template's shared
// node_modules, and Turbopack refuses links that leave its root, so the root is widened to the folder holding both.
// A published site never has it set.
const nextConfig: NextConfig = {
  images: { unoptimized: true },
  // FORGE's preview shared through a tunnel (D-256): next dev accepts these addresses. No effect in production.
  allowedDevOrigins: ["*.trycloudflare.com", "*.ngrok-free.app"],
  ...(process.env.FORGE_TURBOPACK_ROOT ? { turbopack: { root: process.env.FORGE_TURBOPACK_ROOT } } : {}),
}

export default nextConfig
