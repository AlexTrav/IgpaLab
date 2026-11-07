import { describe, expect, it } from 'vitest'
import en from './en'
import kk from './kk'
import ru from './ru'

// переводы: на всех трёх языках одинаковые ключи и ни одного пустого текста; длинного тире нет ни в текстах,
// ни в исходниках сайта

type Tree = { [key: string]: string | Tree }

function entries(tree: Tree, prefix = ''): [string, string][] {
  return Object.entries(tree).flatMap(([k, v]) => (typeof v === 'string' ? [[prefix + k, v] as [string, string]] : entries(v, `${prefix}${k}.`)))
}

const keys = (tree: Tree) => entries(tree).map(([k]) => k).sort()
const sources = import.meta.glob(['../**/*.vue', '../**/*.ts'], { query: '?raw', import: 'default', eager: true }) as Record<string, string>

describe('переводы', () => {
  it('казахский и английский – те же ключи, что русский', () => {
    const base = keys(ru as Tree)
    expect(keys(kk as Tree)).toEqual(base)
    expect(keys(en as Tree)).toEqual(base)
  })

  it('нет пустых текстов', () => {
    for (const tree of [ru, kk, en]) for (const [k, v] of entries(tree as Tree)) expect(v.trim(), k).not.toBe('')
  })

  it('все ключи t(...) в исходниках есть в русском', () => {
    const known = new Set(keys(ru as Tree))
    for (const [file, text] of Object.entries(sources)) {
      for (const m of text.matchAll(/\bt\('([a-zA-Z]+(?:\.[a-zA-Z]+)+)'/g)) expect(known.has(m[1]), `${file}: ${m[1]}`).toBe(true)
    }
  })

  it('длинного тире нет ни в текстах, ни в исходниках', () => {
    const dash = String.fromCharCode(0x2014)
    for (const tree of [ru, kk, en]) expect(JSON.stringify(tree)).not.toContain(dash)
    for (const [file, text] of Object.entries(sources)) expect(text.includes(dash), file).toBe(false)
  })
})
