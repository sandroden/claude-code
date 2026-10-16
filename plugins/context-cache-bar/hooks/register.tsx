import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, SessionContextUsage, SessionRateLimit } from 'claude-code'

import type { Cache, Ctx, Project, Window5h } from '../types'
import type { Segment } from './bar'
import { blocks, cacheBar, clock, COLOR_DIM, contextBar, hhmm, humanTokens, monoSvg, projectSegments, shortDuration, windowColor } from './bar'

const MIN5 = 5 * 60_000
const HOUR = 60 * 60_000

const ctxAtom = atom({ plugin: 'context-cache-bar', key: 'ctx' } as const, null)
const cacheAtom = atom({ plugin: 'context-cache-bar', key: 'cache' } as const, { lastAt: null, ttlMs: MIN5 })
const nowAtom = atom({ plugin: 'context-cache-bar', key: 'now' } as const, 0)
const projectAtom = atom({ plugin: 'context-cache-bar', key: 'project' } as const, null)
const windowAtom = atom({ plugin: 'context-cache-bar', key: 'window5h' } as const, null)
const tzAtom = atom({ plugin: 'context-cache-bar', key: 'tzOffsetMin' } as const, 0)

// Nome progetto, tipo e branch: come render_project di thx-statusline.sh
async function run($: EngineInterface, argv: string[], cwd: string): Promise<string> {
  try {
    const r = await $.process.run(argv, { cwd, timeoutMs: 3000 })
    return r.exitCode === 0 ? r.stdout.trim() : ''
  } catch {
    return ''
  }
}

async function readText($: EngineInterface, path: string): Promise<string | null> {
  try {
    return String(await $.fs.read(path))
  } catch {
    return null
  }
}

async function projectInfo($: EngineInterface): Promise<Project> {
  const cwd = await $.session.cwd()
  const pyproject = await readText($, `${cwd}/pyproject.toml`)

  // name = "..." nella sezione [project]
  const section = pyproject?.split(/^\[project\]\s*$/m)[1]?.split(/^\[/m)[0] ?? ''
  const name = /^name\s*=\s*"([^"]+)"/m.exec(section)?.[1] ?? cwd.split('/').filter(Boolean).pop() ?? cwd

  const isApp = (await $.fs.exists(`${cwd}/Dockerfile`)) || (await $.fs.exists(`${cwd}/manage.py`))
  const type = isApp ? 'app' : pyproject !== null ? 'pkg' : null

  let branch: string | null = null
  if (await $.fs.exists(`${cwd}/.hg`)) {
    const b = await run($, ['hg', 'branch'], cwd)
    const topic = await run($, ['hg', 'topics', '--current'], cwd)
    branch = (topic ? `${b}/${topic}` : b) || null
  } else {
    branch = (await run($, ['git', 'branch', '--show-current'], cwd)) || null
  }
  return { name, type, branch }
}

async function refreshProject($: EngineInterface) {
  const p = await projectInfo($)
  await update($, projectAtom, () => p)
}

function setWindow($: EngineInterface, limits: readonly SessionRateLimit[]) {
  const w = limits.find(l => l.kind === 'five_hour')
  const value: Window5h | null = w ? { percent: w.percentUsed, resetsAt: w.resetsAt ? Date.parse(w.resetsAt) : null } : null
  return update($, windowAtom, () => value)
}

// Offset del fuso locale in minuti, da `date +%z` (es. +0200 -> 120)
async function refreshTz($: EngineInterface) {
  const z = await run($, ['date', '+%z'], await $.session.cwd())
  const m = /^([+-])(\d\d)(\d\d)$/.exec(z)
  if (m) {
    const off = (m[1] === '-' ? -1 : 1) * (Number(m[2]) * 60 + Number(m[3]))
    await update($, tzAtom, () => off)
  }
}

function setCtx($: EngineInterface, c: SessionContextUsage) {
  return update($, ctxAtom, (): Ctx => ({ tokens: c.tokens ?? null, window: c.window, percent: c.percent ?? null }))
}

export const register: Register = (on, options) => {
  const ttlOpt = String(options.ttl ?? 'auto')

  on('session.start', async ($, e, next) => {
    const usage = await $.session.usage()
    await setCtx($, usage.context)
    await setWindow($, usage.rateLimits)
    await refreshTz($)

    // auto: con abbonamento (rate limit riportati) Claude Code usa TTL 1h
    const ttlMs = ttlOpt === '1h' ? HOUR : ttlOpt === '5m' ? MIN5 : usage.rateLimits.length > 0 ? HOUR : MIN5
    await update($, cacheAtom, c => ({ ...c, ttlMs }))
    await refreshProject($)
    const t0 = await $.clock.now()
    await update($, nowAtom, () => t0)

    // Ridisegna ogni secondo finché la cache è calda (più un ultimo tick),
    // altrimenti a ogni cambio di minuto per il tempo residuo della finestra
    $.clock.every(1000, async () => {
      const [c, now, last] = [await read($, cacheAtom), await $.clock.now(), await read($, nowAtom)]
      const isWarm = c.lastAt !== null && now - c.lastAt < c.ttlMs + 2000
      if (isWarm || Math.floor(now / 60_000) !== Math.floor(last / 60_000)) {
        await update($, nowAtom, () => now)
      }
    })
    return next(e)
  })

  on('session.measure', async ($, e, next) => {
    await setCtx($, e.context)
    await setWindow($, e.rateLimits)
    if (ttlOpt === 'auto' && e.rateLimits.length > 0) {
      await update($, cacheAtom, c => (c.ttlMs < HOUR ? { ...c, ttlMs: HOUR } : c))
    }
    return next(e)
  })

  // Ogni richiesta del thread principale rinnova la cache
  on('turn.step', async function* ($, e, next) {
    const startedAt = await $.clock.now()
    const r = yield* next(e)
    if (!e.agentId && r.usage) {
      const usage = r.usage
      await update($, cacheAtom, (c): Cache => {
        // Un hit dopo più di 5 minuti dimostra che il TTL è 1h
        const proves1h = ttlOpt === 'auto' && c.lastAt !== null && startedAt - c.lastAt > MIN5 && usage.cache_read_input_tokens > 0
        return { lastAt: startedAt, ttlMs: proves1h ? HOUR : c.ttlMs }
      })
      await update($, nowAtom, () => startedAt)
    }
    return r
  })

  // Il branch/topic può cambiare durante un turno
  on('turn.complete', async ($, e, next) => {
    await refreshProject($)
    return next(e)
  })

  on('session.end', async ($, e, next) => {
    if (e.reason === 'clear') {
      await update($, cacheAtom, c => ({ ...c, lastAt: null }))
    }
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const ctx = await read($, ctxAtom)
    if (e.props.hasSurvey || ctx === null) {
      return next(e)
    }
    const cache = await read($, cacheAtom)
    const now = await read($, nowAtom)
    const project = await read($, projectAtom)
    const win = await read($, windowAtom)
    const tz = await read($, tzAtom)
    const ui = $.ui.resolve(e)
    const { Box, Text } = ui

    // Dove la superficie ha Svg (desktop) i tempi vanno in monospace, piccolo
    // per la riga progetto; nel terminale è già tutto monospace
    const mono = (key: string, segments: Segment[], fontSize: number, isDim = false) => {
      if ('Svg' in ui) {
        const svg = monoSvg(segments, fontSize)
        return <ui.Svg key={key} source={svg.source} alt={svg.alt} width={svg.width} height={svg.height} />
      }
      return (
        <Text key={key} dimColor={isDim}>
          {segments.map((sg, i) => <Text key={String(i)} color={isDim ? undefined : sg.color}>{sg.text}</Text>)}
        </Text>
      )
    }

    const pct = ctx.percent ?? 0
    const cb = contextBar(pct, ctx.window)
    const [cOn, cOff] = blocks(cb.filled, cb.total)
    const used = ctx.tokens ?? Math.round((ctx.window * pct) / 100)

    let cacheRow = <Text dimColor>cache —</Text>
    if (cache.lastAt !== null) {
      const remaining = cache.lastAt + cache.ttlMs - now
      const kb = cacheBar(remaining, cache.ttlMs)
      const [kOn, kOff] = blocks(kb.filled, kb.total)
      const ttl = cache.ttlMs >= HOUR ? '1h' : '5m'
      const time = remaining > 0 ? clock(remaining).padStart(cache.ttlMs >= HOUR ? 5 : 4, ' ') : 'fredda'
      cacheRow = (
        <Box flexDirection="row" alignItems="center">
          <Text>cache [<Text color={kb.color}>{kOn}</Text><Text dimColor>{kOff}</Text>] </Text>
          {mono('cache-time', [{ text: time, color: kb.color }, { text: ` /${ttl}`, color: COLOR_DIM }], 14)}
        </Box>
      )
    }

    let windowRow = null
    if (win !== null) {
      const color = windowColor(win.percent)
      const segs: Segment[] = [{ text: `${Math.round(win.percent)}%`.padStart(4, ' '), color }]
      if (win.resetsAt !== null) {
        segs.push({ text: ' fine ', color: COLOR_DIM }, { text: hhmm(win.resetsAt, tz), color })
        segs.push({ text: ` (${shortDuration(win.resetsAt - now)})`, color: COLOR_DIM })
      }
      windowRow = (
        <Box flexDirection="row" alignItems="center">
          <Text>sessione </Text>
          {mono('window', segs, 14)}
        </Box>
      )
    }

    return (
      <Box flexDirection="row" justifyContent="space-between" width={e.props.bodyColumns}>
        <Box flexDirection="column">
          <Text wrap="truncate-end">
            ctx [<Text color={cb.color}>{cOn}</Text><Text dimColor>{cOff}</Text>]{' '}
            <Text bold color={cb.color}>{pct}%</Text>
            <Text dimColor> ({humanTokens(used)}/{humanTokens(ctx.window)})</Text>
          </Text>
          {project !== null ? mono('project', projectSegments(project), 11, true) : null}
        </Box>
        <Box flexDirection="column" alignItems="flex-end">
          {cacheRow}
          {windowRow}
        </Box>
      </Box>
    )
  })
}
