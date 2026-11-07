import { describe, expect, it } from 'vitest'
import quick from '../test/fixtures/quick.json'
import { gpaForTarget, igpaParts, shares } from './igpa'

// формула сайта должна совпадать с калькулятором API (ответ /api/quick для GPA 3,1, iROS 0,2, SSCI 0,3)
describe('формула IGPA', () => {
  it('совпадает с ответом API', () => {
    const p = igpaParts(3.1, 0.2, 0.3)
    for (const row of quick) {
      expect(p.igpa).toBeCloseTo(row.igpa, 10)
      expect(p.gpa).toBeCloseTo(row.gpa_part, 10)
      expect(p.iros).toBeCloseTo(row.iros_part, 10)
      expect(p.ssci).toBeCloseTo(row.ssci_part, 10)
    }
  })

  it('максимум шкалы – 4, значения за пределами обрезаются', () => {
    expect(igpaParts(4, 1, 1).igpa).toBeCloseTo(4, 10)
    expect(igpaParts(5, 2, -1).igpa).toBeCloseTo(0.5 * 4 + 0.35 * 4, 10)
  })

  it('обратный расчёт: найденный GPA даёт целевой IGPA', () => {
    const gpa = gpaForTarget(2.0, 0.2, 0.3)!
    expect(gpa).toBeCloseTo(3.08, 10)
    expect(igpaParts(gpa, 0.2, 0.3).igpa).toBeCloseTo(2.0, 10)
    expect(gpaForTarget(2.5, 0.2, 0.3)).toBeNull() // нужен GPA 4,08 – выше шкалы
    expect(gpaForTarget(3.9, 0, 0)).toBeNull() // даже GPA 4,0 даёт только 2,0
    expect(gpaForTarget(0.1, 0.5, 0.5)).toBe(0) // доли уже дают больше цели
  })

  it('доли полосы складываются в долю IGPA от шкалы', () => {
    const s = shares(igpaParts(3, 0.5, 0.5))
    expect(s.gpa + s.iros + s.ssci).toBeCloseTo((igpaParts(3, 0.5, 0.5).igpa / 4) * 100, 10)
  })
})
