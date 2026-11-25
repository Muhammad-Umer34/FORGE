// Free times for a booking form (D-247): the date and the visitor's picks (e.g. staff_id, service_id) go to FORGE.
import { forge } from "@/lib/forge"

type Ctx = { params: Promise<{ table: string }> }

export async function GET(request: Request, ctx: Ctx) {
  const { table } = await ctx.params
  if (!/^[a-z][a-z0-9_]{0,40}$/.test(table)) return Response.json({ ok: false, message: "No such form." }, { status: 404 })
  const query = new URL(request.url).searchParams
  const kept = new URLSearchParams()
  query.forEach((value, name) => {
    if (/^[a-z][a-z0-9_]{0,40}$/.test(name) && value.length <= 64) kept.set(name, value)
  })
  const answer = await forge(`${table}/availability?${kept.toString()}`, { method: "GET" })
  return Response.json(answer.body, { status: answer.status })
}
