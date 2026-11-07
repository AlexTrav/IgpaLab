import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope, nextTick } from 'vue'

const calls: { gpa: number; rules: string }[] = []
vi.mock('../api/client', () => ({
  api: {
    portfolio: vi.fn(async (body: { gpa: number; rules: string }) => {
      calls.push(body)
      return { now: { igpa: body.gpa / 2, rules: body.rules } }
    }),
  },
}))

describe('портфель пересчитывается при изменениях', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('после ухода со страницы и возврата GPA и правило уходят в новый запрос', async () => {
    const { usePortfolio } = await import('./usePortfolio')
    // первое открытие «Моего портфеля» и уход на другую страницу: Vue останавливает всё, что создала страница
    const page = effectScope()
    page.run(() => usePortfolio())
    await vi.runAllTimersAsync()
    expect(calls).toHaveLength(1)
    page.stop()

    const { state, result } = usePortfolio()
    state.gpa = 1.45
    state.rules = 'percentile'
    await nextTick()
    await vi.advanceTimersByTimeAsync(500)
    expect(calls).toHaveLength(2)
    expect(calls[1]).toMatchObject({ gpa: 1.45, rules: 'percentile' })
    expect(result.value?.now.rules).toBe('percentile')
  })
})
