import { describe, expect, it } from 'vitest'
import { scrollTarget } from './scroll'

const quick = { path: '/quick', hash: '' }

describe('прокрутка при переходах', () => {
  it('ползунок меняет только query – страница остаётся на месте', () => {
    expect(scrollTarget(quick, quick, null)).toBe(false)
  })

  it('новая страница – наверх', () => {
    expect(scrollTarget({ path: '/research', hash: '' }, quick, null)).toEqual({ top: 0 })
  })

  it('назад и вперёд – на прежнее место, якорь – к нему', () => {
    expect(scrollTarget(quick, { path: '/', hash: '' }, { left: 0, top: 640 })).toEqual({ left: 0, top: 640 })
    expect(scrollTarget({ path: '/about', hash: '#data' }, { path: '/about', hash: '' }, null)).toEqual({ el: '#data', top: 80 })
  })
})
