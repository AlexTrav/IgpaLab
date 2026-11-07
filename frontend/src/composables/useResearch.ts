import { ref, watch } from 'vue'
import { api } from '../api/client'
import { i18n } from '../i18n'
import type { AppLocale, Research, ResearchRow } from '../types'

// результаты исследования (одна загрузка на язык: от языка зависят только названия признаков)
const cache = new Map<AppLocale, Promise<Research>>()
const research = ref<Research | null>(null)
const failed = ref(false)
let started = false

function fetchResearch(lang: AppLocale): Promise<Research> {
  return api.research(lang).then(({ feature_names, ...tables }) => ({ tables: tables as Record<string, ResearchRow[]>, names: feature_names ?? {} }))
}

function load(lang: AppLocale) {
  if (!cache.has(lang)) cache.set(lang, fetchResearch(lang).catch((e) => (cache.delete(lang), Promise.reject(e))))
  failed.value = false
  cache.get(lang)!.then((r) => (research.value = r)).catch(() => (failed.value = true))
}

export function useResearch() {
  if (!started) {
    started = true
    watch(() => i18n.global.locale.value as AppLocale, load, { immediate: true })
  }
  return { research, failed, retry: () => load(i18n.global.locale.value as AppLocale) }
}

// строки таблицы по условию и числовое поле
export const rows = (r: Research | null, key: string, where: Record<string, unknown> = {}): ResearchRow[] =>
  (r?.tables[key] ?? []).filter((row) => Object.entries(where).every(([k, v]) => row[k] === v))
export const val = (row: ResearchRow | undefined, key: string): number | null => (row && typeof row[key] === 'number' ? (row[key] as number) : null)
