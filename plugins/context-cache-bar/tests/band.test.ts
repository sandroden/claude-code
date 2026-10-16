import { expect, test } from 'claude-code/testing'

// Istante fisso: 08:00 UTC, fuso +0200
const NOW = Date.parse('2026-10-16T08:00:00Z')
const RESET = '2026-10-16T10:40:00Z'

const BAND = {
  plugin: 'context-cache-bar',
  component: 'AbovePrompt',
  props: { hasSurvey: false, isWorking: false, maxRows: 10, bodyColumns: 100, scroll: { offset: 0, bodyRows: 10 }, view: {} },
} as const

test('la banda mostra tempi, sessione e progetto nel terminale e nel desktop', async ($, on) => {
  on('clock.now', () => ({ value: NOW }))
  on('session.cwd', () => ({ value: '/home/u/proactivity' }))
  on('session.usage', () => ({
    value: {
      startedAt: NOW,
      context: { tokens: 209_000, window: 1_000_000, percent: 21 },
      rateLimits: [{ kind: 'five_hour', percentUsed: 3, resetsAt: RESET }],
    },
  }))
  on('process.run', ($, e) => ({ value: { exitCode: 0, stdout: e.argv[0] === 'date' ? '+0200\n' : '', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }))
  on('fs.read', () => ({ deny: 'missing' }))
  on('fs.exists', () => ({ value: false }))
  on('session.start', ($, e) => ({ cwd: e.cwd }))
  on('turn.step', async function* ($, e) {
    return {
      turnId: e.turnId, index: e.index, answer: 'ok', toolUses: [], stopReason: 'end_turn',
      usage: { model: e.model, input_tokens: 10, output_tokens: 5, cache_read_input_tokens: 0, cache_creation_input_tokens: 100 },
    }
  })

  await $.session.start({ cwd: '/home/u/proactivity', surface: 'terminal', isInteractive: true })
  // una richiesta del thread principale: la cache parte da NOW
  const stream = $.turn.step({ turnId: 't1', index: 0, model: 'claude-opus-5-5', messageCount: 1 })
  for await (const _ of stream) { /* nessun chunk */ }

  const term = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await term.find({ type: 'Text', text: /1:00:00/ })).toBeDefined()
  expect(await term.find({ type: 'Text', text: /fine 12:40/ })).toBeDefined()
  expect(await term.find({ type: 'Text', text: /proactivity/ })).toBeDefined()
  expect(await term.find({ type: 'Svg' })).toBeUndefined()
  await term.unmount()

  const desk = await $.ui.mount({ ...BAND, surface: 'desktop' })
  const svgs = await desk.findAll({ type: 'Svg' })
  const alts = svgs.map(el => String(el.props.alt))
  expect(alts.some(a => a.includes('1:00:00'))).toBe(true)
  expect(alts.some(a => a.includes('fine 12:40'))).toBe(true)
  expect(alts).toContain('proactivity')
  await desk.unmount()
})
