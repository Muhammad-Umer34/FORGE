// Runs before every /api/* call is forwarded to FastAPI. It changes nothing, but when a proxy exists Next.js
// sets X-Forwarded-For to the visitor's real address, which the backend's per-address limits need (D-189);
// without it every visitor arrives as 127.0.0.1 and shares one counter.
// shortcut: a visitor who sends their own X-Forwarded-For keeps it (Next.js does not overwrite it), so per-address
// limits can be dodged; in production put Caddy or nginx in front, set to replace that header with the real address.
import { NextResponse } from "next/server";

export function proxy() {
  return NextResponse.next();
}

export const config = { matcher: "/api/:path*" };
