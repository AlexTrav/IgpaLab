import { describe, expect, it } from 'vitest'
import { num, pct, signed } from './format'

const nbsp = (s: string) => s.replace(/[\u00a0\u202f]/g, ' ')

describe('форматирование чисел', () => {
  it('запятая для русского и казахского, точка для английского', () => {
    expect(num(1.5, 'ru')).toBe('1,50')
    expect(num(1.5, 'kk')).toBe('1,50')
    expect(num(1.5, 'en')).toBe('1.50')
    expect(nbsp(num(6000, 'ru', 0))).toBe('6 000')
  })

  it('проценты и знак', () => {
    expect(pct(0.234, 'ru')).toBe('23%')
    expect(signed(0.1, 'ru')).toBe('+0,10')
    expect(signed(-0.04, 'en')).toBe('\u22120.04')
    expect(num(null, 'ru')).toBe('–')
  })
})
