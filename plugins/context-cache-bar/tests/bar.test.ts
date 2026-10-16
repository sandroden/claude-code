import { expect, test } from 'claude-code/testing'

import { cacheBar, clock, contextBar, hhmm, humanTokens, monoSvg, shortDuration, windowColor } from '../hooks/bar'

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

test('finestra 5h: ora locale, durata e colore', async () => {
  // 16:40 UTC con fuso +0200 -> 18:40
  expect(hhmm(Date.parse('2026-10-16T16:40:00Z'), 120)).toBe('18:40')
  expect(hhmm(Date.parse('2026-10-16T00:10:00Z'), -300)).toBe('19:10')
  expect(shortDuration(133 * 60_000)).toBe('2h13m')
  expect(shortDuration(45 * 60_000)).toBe('45m')
  expect(windowColor(30)).toBe('#3fb950')
  expect(windowColor(85)).toBe('#f85149')
})

test('monoSvg: larghezza proporzionale ai caratteri, testo escapato', async () => {
  const a = monoSvg([{ text: '59:22', color: '#fff' }], 14)
  const b = monoSvg([{ text: '9:22', color: '#fff' }], 14)
  expect(a.width).toBeGreaterThan(b.width)
  expect(monoSvg([{ text: 'a<b', color: '#fff' }], 11).source).toContain('a&lt;b')
})
