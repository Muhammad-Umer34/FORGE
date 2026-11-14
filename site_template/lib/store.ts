// Where a generated site keeps what visitors send (D-227). Route handlers call only these two functions.
// The backend compiler fills the adapters: "memory" for the preview (seeded sample rows, lost on reload) and
// "forge" for a published site (posts to the FORGE submissions service with the site's key, server side only).

export type Row = Record<string, unknown>

export interface Store {
  add(entity: string, row: Row): Promise<{ id: string }>
  list(entity: string): Promise<Row[]>
}

const memory: Record<string, Row[]> = {}

export const store: Store = {
  async add(entity, row) {
    const id = crypto.randomUUID()
    ;(memory[entity] ??= []).push({ id, ...row })
    return { id }
  },
  async list(entity) {
    return memory[entity] ?? []
  },
}
