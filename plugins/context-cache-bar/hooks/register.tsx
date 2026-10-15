import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, SessionContextUsage } from 'claude-code'

import type { Cache, Ctx, Project } from '../types'
import { blocks, cacheBar, clock, contextBar, humanTokens, projectSvg } from './bar'

const MIN5 = 5 * 60_000
const HOUR = 60 * 60_000

const ctxAtom = atom({ plugin: 'context-cache-bar', key: 'ctx' } as const, null)
const cacheAtom = atom({ plugin: 'context-cache-bar', key: 'cache' } as const, { lastAt: null, ttlMs: MIN5 })
const nowAtom = atom({ plugin: 'context-cache-bar', key: 'now' } as const, 0)
const projectAtom = atom({ plugin: 'context-cache-bar', key: 'project' } as const, null)

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

function setCtx($: EngineInterface, c: SessionContextUsage) {
  return update($, ctxAtom, (): Ctx => ({ tokens: c.tokens ?? null, window: c.window, percent: c.percent ?? null }))
}

export const register: Register = (on, options) => {
  const ttlOpt = String(options.ttl ?? 'auto')

  on('session.start', async ($, e, next) => {
    const usage = await $.session.usage()
    await setCtx($, usage.context)

    // auto: con abbonamento (rate limit riportati) Claude Code usa TTL 1h
    const ttlMs = ttlOpt === '1h' ? HOUR : ttlOpt === '5m' ? MIN5 : usage.rateLimits.length > 0 ? HOUR : MIN5
    await update($, cacheAtom, c => ({ ...c, ttlMs }))
    await refreshProject($)
    const t0 = await $.clock.now()
    await update($, nowAtom, () => t0)

    // Ridisegna ogni secondo finché la cache è calda (più un ultimo tick)
    $.clock.every(1000, async () => {
      const [c, now] = [await read($, cacheAtom), await $.clock.now()]
      if (c.lastAt !== null && now - c.lastAt < c.ttlMs + 2000) {
        await update($, nowAtom, () => now)
      }
    })
    return next(e)
  })

  on('session.measure', async ($, e, next) => {
    await setCtx($, e.context)
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
    const ui = $.ui.resolve(e)
    const { Box, Text } = ui

    const pct = ctx.percent ?? 0
    const cb = contextBar(pct, ctx.window)
    const [cOn, cOff] = blocks(cb.filled, cb.total)
    const used = ctx.tokens ?? Math.round((ctx.window * pct) / 100)

    let cachePart = <Text dimColor>cache —</Text>
    if (cache.lastAt !== null) {
      const remaining = cache.lastAt + cache.ttlMs - now
      const kb = cacheBar(remaining, cache.ttlMs)
      const [kOn, kOff] = blocks(kb.filled, kb.total)
      const ttl = cache.ttlMs >= HOUR ? '1h' : '5m'
      cachePart = (
        <Text>
          cache [<Text color={kb.color}>{kOn}</Text><Text dimColor>{kOff}</Text>]{' '}
          <Text bold color={kb.color}>{remaining > 0 ? clock(remaining) : 'fredda'}</Text>
          <Text dimColor> /{ttl}</Text>
        </Text>
      )
    }

    // Seconda riga: piccola (SVG) dove la superficie lo disegna, altrimenti attenuata
    let projectRow = null
    if (project !== null) {
      if ('Svg' in ui) {
        const svg = projectSvg(project)
        projectRow = <ui.Svg source={svg.source} alt={svg.alt} width={svg.width} height={svg.height} />
      } else {
        projectRow = (
          <Text dimColor wrap="truncate-end">
            {project.name}{project.type ? `(${project.type})` : ''}{project.branch ? ` @${project.branch}` : ''}
          </Text>
        )
      }
    }

    return (
      <Box flexDirection="column" width={e.props.bodyColumns}>
        <Box flexDirection="row" justifyContent="space-between">
          <Text wrap="truncate-end">
            ctx [<Text color={cb.color}>{cOn}</Text><Text dimColor>{cOff}</Text>]{' '}
            <Text bold color={cb.color}>{pct}%</Text>
            <Text dimColor> ({humanTokens(used)}/{humanTokens(ctx.window)})</Text>
          </Text>
          {cachePart}
        </Box>
        {projectRow}
      </Box>
    )
  })
}
