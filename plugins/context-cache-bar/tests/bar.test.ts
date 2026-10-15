import { expect, test } from 'claude-code/testing'

import { cacheBar, clock, contextBar, humanTokens } from '../hooks/bar'

test('finestra 1M: a 150k (15%) è già oltre la zona verde', async () => {
  const b = contextBar(15, 1_000_000)
  expect(b.total).toBe(12)
  expect(b.filled).toBe(4)
  expect(b.color).toBe('#e3b341')
})

test('finestra 200k: 70% è giallo, 80% rosso pieno', async () => {
  expect(contextBar(70, 200_000).color).toBe('#f0883e')
  const over = contextBar(80, 200_000)
  expect(over.filled).toBe(over.total)
  expect(over.color).toBe('#f85149')
})

test('cache: colori per quota residua e fredda a zero', async () => {
  expect(cacheBar(50 * 60_000, 60 * 60_000).color).toBe('#3fb950')
  expect(cacheBar(90_000, 5 * 60_000).color).toBe('#e3b341')
  expect(cacheBar(30_000, 5 * 60_000).color).toBe('#f85149')
  expect(cacheBar(0, 5 * 60_000).filled).toBe(0)
})

test('formati', async () => {
  expect(humanTokens(156_000)).toBe('156K')
  expect(humanTokens(1_000_000)).toBe('1M')
  expect(clock(221_000)).toBe('3:41')
  expect(clock(3_600_000)).toBe('1:00:00')
})
