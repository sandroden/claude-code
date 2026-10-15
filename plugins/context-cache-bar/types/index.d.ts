export type Ctx = { tokens: number | null; window: number; percent: number | null }
export type Cache = { lastAt: number | null; ttlMs: number }
export type Project = { name: string; type: string | null; branch: string | null }

declare module 'claude-code' {
  interface PluginState {
    'context-cache-bar': { ctx: Ctx | null; cache: Cache; now: number; project: Project | null }
  }
}
