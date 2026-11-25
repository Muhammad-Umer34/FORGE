// Every form and list of this site (D-247): checked here against lib/schemas.ts, then sent to FORGE with the site's
// secret key. FORGE checks again against the site's contract; the database has the final word.
import { forge } from "@/lib/forge"
import { schemas } from "@/lib/schemas"

type Ctx = { params: Promise<{ table: string }> }

function reply(status: number, body: Record<string, unknown>) {
  return Response.json(body, { status })
}

export async function POST(request: Request, ctx: Ctx) {
  const { table } = await ctx.params
  const schema = schemas[table]
  if (!schema) return reply(404, { ok: false, message: "This site does not take that form." })
  const body = await request.json().catch(() => null)
  const checked = schema.safeParse(body)
  if (!checked.success) {
    const issue = checked.error.issues[0]
    return reply(422, { ok: false, message: issue?.message ?? "Please check the form.", field: issue?.path[0] ?? null })
  }
  const answer = await forge(table, { method: "POST", body: checked.data })
  return reply(answer.status, answer.body)
}

export async function GET(_request: Request, ctx: Ctx) {
  const { table } = await ctx.params
  if (!/^[a-z][a-z0-9_]{0,40}$/.test(table)) return reply(404, { ok: false, message: "No such list." })
  const answer = await forge(table, { method: "GET" })
  return reply(answer.status, answer.body)
}
