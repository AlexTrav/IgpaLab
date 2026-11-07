import { describe, expect, it } from 'vitest'
import { ALIVE_MS, nextStatus, type StatusMemory } from './serverStatus'

const fresh: StatusMemory = { status: 'unknown', lastOk: -Infinity, lastFail: -Infinity }

describe('плашка состояния сервера', () => {
  it('долгий ответ спящего сервера – «просыпается», ответ – плашка исчезает', () => {
    const waking = nextStatus(fresh, 'slow', 3_000, 0)
    expect(waking.status).toBe('waking')
    expect(nextStatus(waking, 'ok', 50_000, 0).status).toBe('ready')
  })

  it('502/503/504 от прокси Render – тоже «просыпается», а не «не отвечает»', () => {
    expect(nextStatus(fresh, 'waking', 1_000, 0).status).toBe('waking')
  })

  it('сеть недоступна – «не отвечает»', () => {
    expect(nextStatus(fresh, 'fail', 1_000, 0).status).toBe('down')
  })

  it('после падения зависшие соседние запросы не возвращают «просыпается»', () => {
    const down = nextStatus(fresh, 'fail', 1_000, 0)
    expect(nextStatus(down, 'slow', 2_500, 0).status).toBe('down') // запрос начат до падения
    expect(nextStatus(down, 'slow', 9_000, 6_000).status).toBe('waking') // новый запрос, например «Повторить»
  })

  it('сервер отвечал недавно – медленный или упавший запрос плашку не включает', () => {
    const ready = nextStatus(fresh, 'ok', 10_000, 0)
    expect(nextStatus(ready, 'slow', 12_000, 9_000).status).toBe('ready')
    expect(nextStatus(ready, 'fail', 12_000, 9_000).status).toBe('ready')
    expect(nextStatus(ready, 'slow', 10_000 + ALIVE_MS + 1, 10_000 + ALIVE_MS - 2_000).status).toBe('waking')
  })
})
