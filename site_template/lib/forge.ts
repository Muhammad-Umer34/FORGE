// How the site's server reaches its data (D-247): every form and list goes through FORGE's site data API with this
// site's secret key. Only route handlers import this file; the key never reaches the browser.

const TIMEOUT_MS = 20_000          // the first request of a minute may wait for a new database connection

export interface ForgeAnswer {
  status: number
  body: Record<string, unknown>
}

function connected(): { url: string; key: string } | null {
  const url = process.env.FORGE_API_URL
  const key = process.env.FORGE_SITE_KEY
  return url && key ? { url: url.replace(/\/$/, ""), key } : null
}

/** Ask FORGE; FORGE's own status and plain message are passed back to the visitor unchanged. */
export async function forge(path: string, init: { method: "GET" | "POST"; body?: unknown }): Promise<ForgeAnswer> {
  const link = connected()
  if (!link) {
    return { status: 503, body: { ok: false, message: "Saving is not switched on for this preview yet." } }
  }
  try {
    const res = await fetch(`${link.url}/api/site-data/${path}`, {
      method: init.method,
      headers: { "Content-Type": "application/json", "X-Forge-Site-Key": link.key },
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
      cache: "no-store",
      signal: AbortSignal.timeout(TIMEOUT_MS),
    })
    const body = (await res.json().catch(() => ({}))) as Record<string, unknown>
    return { status: res.status, body }
  } catch {
    return { status: 502, body: { ok: false, message: "We couldn't reach our booking system. Please try again." } }
  }
}
