import { useDebounceFn } from '@vueuse/core'
import { computed, reactive, ref, watch } from 'vue'
import { api } from '../api/client'
import { i18n } from '../i18n'
import type { AppLocale, Level, Portfolio, RecordIn, RulesCode } from '../types'
import type { Sample } from '../utils/samples'

// «Мой портфель»: ввод хранится только в браузере (localStorage), расчёт – запросом к API с задержкой 400 мс после
// последнего изменения; пока идёт новый расчёт, на экране остаётся прошлый результат
const STORAGE_KEY = 'igpalab-portfolio'

export interface PortfolioState {
  gpa: number
  hasPrev: boolean
  gpaPrev: number
  level: Level
  year: number
  rules: RulesCode
  records: (RecordIn & { id: number })[]
}

export const MAX_YEAR: Record<Level, number> = { bachelor: 4, master_research: 2, master_profile: 1 }

const DEFAULT: PortfolioState = { gpa: 3.0, hasPrev: true, gpaPrev: 2.9, level: 'bachelor', year: 2, rules: 'default', records: [] }

function restore(): PortfolioState {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null')
    if (saved && typeof saved.gpa === 'number' && Array.isArray(saved.records)) return { ...DEFAULT, ...saved }
  } catch {
    // повреждённое или недоступное хранилище – начинаем с примера по умолчанию
  }
  return structuredClone(DEFAULT)
}

let nextId = 1
const state = reactive<PortfolioState>(restore())
for (const r of state.records) nextId = Math.max(nextId, r.id + 1)

const result = ref<Portfolio | null>(null)
const loading = ref(false)
const error = ref(false)
let seq = 0

watch(
  state,
  (s) => {
    if (s.year > MAX_YEAR[s.level]) s.year = MAX_YEAR[s.level]
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(s))
    } catch {
      // не критично – портфель просто не запомнится
    }
  },
  { deep: true },
)

async function compute() {
  const my = ++seq // ответ на устаревший запрос не перетирает свежий
  loading.value = true
  error.value = false
  try {
    const res = await api.portfolio({
      gpa: state.gpa,
      gpa_prev: state.hasPrev ? state.gpaPrev : null,
      year_of_study: Math.min(state.year, MAX_YEAR[state.level]),
      level: state.level,
      rules: state.rules,
      records: state.records.map(({ category, status }) => ({ category, status })),
      lang: i18n.global.locale.value as AppLocale,
    })
    if (my === seq) result.value = res
  } catch {
    if (my === seq) error.value = true
  } finally {
    if (my === seq) loading.value = false
  }
}
const schedule = useDebounceFn(compute, 400)
let started = false

export function usePortfolio() {
  if (!started) {
    started = true
    watch([state, () => i18n.global.locale.value], schedule, { deep: true })
    compute()
  }

  function add(category: string, status: string) {
    state.records.unshift({ id: nextId++, category, status })
  }
  function remove(id: number) {
    state.records = state.records.filter((r) => r.id !== id)
  }
  function clear() {
    state.records = []
  }
  function loadSample(s: Sample) {
    Object.assign(state, { gpa: s.gpa, hasPrev: true, gpaPrev: s.gpa_prev, level: 'bachelor', year: s.year_of_study })
    state.records = s.records.map((r) => ({ ...r, id: nextId++ }))
  }
  const counts = computed(() => ({
    iros: state.records.filter((r) => r.category.startsWith('IROS')).length,
    ssci: state.records.filter((r) => r.category.startsWith('SSCI')).length,
  }))
  return { state, result, loading, error, add, remove, clear, loadSample, counts, retry: compute }
}
