import { computed, ref, watch } from 'vue'
import { api } from '../api/client'
import { i18n } from '../i18n'
import type { AppLocale, Meta } from '../types'

// справочники АСУ (16 типов, 9 статусов, правила) с названиями на текущем языке; одна загрузка на язык
const cache = new Map<AppLocale, Promise<Meta>>()
const meta = ref<Meta | null>(null)
const error = ref(false)
let started = false

function load(lang: AppLocale) {
  if (!cache.has(lang)) cache.set(lang, api.meta(lang).catch((e) => (cache.delete(lang), Promise.reject(e))))
  error.value = false
  cache
    .get(lang)!
    .then((m) => {
      if ((i18n.global.locale.value as AppLocale) === lang) meta.value = m
    })
    .catch(() => (error.value = true))
}

export function useMeta() {
  if (!started) {
    started = true
    watch(() => i18n.global.locale.value as AppLocale, load, { immediate: true })
  }
  const categories = computed(() => new Map((meta.value?.categories ?? []).map((c) => [c.code, c])))
  const statuses = computed(() => new Map((meta.value?.statuses ?? []).map((s) => [s.code, s])))
  return { meta, error, categories, statuses, retry: () => load(i18n.global.locale.value as AppLocale) }
}
