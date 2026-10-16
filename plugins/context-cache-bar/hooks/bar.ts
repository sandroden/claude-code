// Logica pura della barra, ripresa da ~/.claude/scripts/thx-statusline.sh

type Profile = { window: number; thresholds: readonly number[] }

// Soglie in % della finestra; oltre l'ultima = rosso.
// Si usa il primo profilo con finestra >= a quella del modello,
// se la finestra è più grande di tutte, l'ultimo.
const PROFILES: readonly [Profile, ...Profile[]] = [
  { window: 200_000, thresholds: [40, 55, 75] },
  { window: 1_000_000, thresholds: [12, 25, 60] },
]

export const BLOCKS_PER_ZONE = 4
// verde, ambra, giallo; poi rosso
export const ZONE_COLORS = ['#3fb950', '#e3b341', '#f0883e'] as const
export const COLOR_OVER = '#f85149'
export const COLOR_COLD = '#8b949e'

export function selectThresholds(window: number): readonly number[] {
  const p = PROFILES.find(p => window <= p.window) ?? PROFILES[PROFILES.length - 1]!
  return p.thresholds
}

// Ogni zona ha lo stesso numero di blocchi, riempiti linearmente dentro la
// zona: la barra non è lineare rispetto alla percentuale
export function contextBar(pct: number, window: number): { filled: number; total: number; color: string } {
  const t = selectThresholds(window)
  const total = t.length * BLOCKS_PER_ZONE
  let start = 0
  for (const [i, end] of t.entries()) {
    if (pct <= end) {
      const b0 = i * BLOCKS_PER_ZONE
      const filled = end === start ? b0 + BLOCKS_PER_ZONE : Math.floor(b0 + ((pct - start) / (end - start)) * BLOCKS_PER_ZONE)
      return { filled, total, color: ZONE_COLORS[i] ?? COLOR_OVER }
    }
    start = end
  }
  return { filled: total, total, color: COLOR_OVER }
}

// Barra del tempo residuo della cache: si svuota, colore per quota rimasta
export function cacheBar(remainingMs: number, ttlMs: number, total = 8): { filled: number; total: number; color: string } {
  if (remainingMs <= 0) return { filled: 0, total, color: COLOR_COLD }
  const frac = remainingMs / ttlMs
  const color = frac > 0.5 ? ZONE_COLORS[0] : frac > 0.2 ? ZONE_COLORS[1] : COLOR_OVER
  return { filled: Math.max(1, Math.ceil(frac * total)), total, color }
}

export function humanTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`
  return `${Math.round(n / 1000)}K`
}

export function clock(ms: number): string {
  const s = Math.max(0, Math.ceil(ms / 1000))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const ss = String(s % 60).padStart(2, '0')
  return h > 0 ? `${h}:${String(m).padStart(2, '0')}:${ss}` : `${m}:${ss}`
}

export const blocks = (filled: number, total: number) => ['█'.repeat(filled), '░'.repeat(total - filled)] as const

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

export type Segment = { text: string; color: string }

// Testo monospace in SVG: cifre a larghezza fissa, non "ballano" mentre scorrono
export function monoSvg(segments: readonly Segment[], fontSize: number) {
  const alt = segments.map(s => s.text).join('')
  const width = Math.ceil(alt.length * fontSize * 0.62) + 2
  const height = Math.ceil(fontSize * 1.35)
  const spans = segments.map(s => `<tspan fill="${s.color}">${esc(s.text)}</tspan>`).join('')
  const source =
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">` +
    `<text x="0" y="${Math.round(fontSize * 1.02)}" font-family="ui-monospace, Menlo, Consolas, 'DejaVu Sans Mono', monospace" ` +
    `font-size="${fontSize}" xml:space="preserve">${spans}</text></svg>`
  return { source, alt, width, height }
}

export const COLOR_DIM = '#8b949e'

// Riga progetto: nome giallo, (tipo) grigio, @branch ciano
export function projectSegments(p: { name: string; type: string | null; branch: string | null }): Segment[] {
  const out: Segment[] = [{ text: p.name, color: '#d29922' }]
  if (p.type) out.push({ text: `(${p.type})`, color: COLOR_DIM })
  if (p.branch) out.push({ text: ` @${p.branch}`, color: '#39c5cf' })
  return out
}

// Colore della finestra a 5 ore per quota usata
export function windowColor(percent: number): string {
  return percent < 50 ? ZONE_COLORS[0] : percent < 80 ? ZONE_COLORS[1] : COLOR_OVER
}

// Ora locale HH:MM di un istante, dato l'offset del fuso in minuti
export function hhmm(ms: number, tzOffsetMin: number): string {
  const d = new Date(ms + tzOffsetMin * 60_000)
  return `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`
}

// Durata compatta: 2h13m, 45m
export function shortDuration(ms: number): string {
  const m = Math.max(0, Math.ceil(ms / 60_000))
  return m >= 60 ? `${Math.floor(m / 60)}h${String(m % 60).padStart(2, '0')}m` : `${m}m`
}
