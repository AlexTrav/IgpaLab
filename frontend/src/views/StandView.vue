<script setup lang="ts">
import { refDebounced } from '@vueuse/core'
import { ChevronLeft, ChevronRight, Dices, RefreshCw, Search, UserRound } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { api } from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import { useMeta } from '../composables/useMeta'
import type { AppLocale, Level, StudentsPage } from '../types'
import { int } from '../utils/format'

// «Студент со стенда»: поиск по 6 000 синтетическим студентам (ФИО, код, программа), фильтры и случайный студент
const { t, locale } = useI18n()
const router = useRouter()
const { meta } = useMeta()
const LIMIT = 20

const query = ref('')
const faculty = ref('')
const level = ref<Level | ''>('')
const current = ref(true)
const page = ref(0)
const debounced = refDebounced(query, 350)
const data = ref<StudentsPage | null>(null)
const loading = ref(false)
const failed = ref(false)

async function load() {
  loading.value = true
  failed.value = false
  try {
    data.value = await api.students({
      q: debounced.value.trim(),
      faculty: faculty.value,
      level: level.value,
      current: current.value,
      limit: LIMIT,
      offset: page.value * LIMIT,
    })
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}
watch([debounced, faculty, level, current], () => {
  page.value = 0
  load()
})
watch(page, load)
load()

const pages = computed(() => Math.max(1, Math.ceil((data.value?.total ?? 0) / LIMIT)))

// случайный студент из текущей выборки: один запрос со случайным сдвигом
async function random() {
  const total = data.value?.total ?? 0
  if (!total) return
  const res = await api.students({ q: debounced.value.trim(), faculty: faculty.value, level: level.value, current: current.value, limit: 1, offset: Math.floor(Math.random() * total) })
  if (res.items[0]) router.push(`/stand/${res.items[0].student_id}`)
}
</script>

<template>
  <div>
    <PageHeader :eyebrow="t('nav.stand')" :title="t('stand.title')" :lead="t('stand.lead')">
      <button v-ripple class="btn-primary" :disabled="!data?.total" @click="random"><Dices class="h-4 w-4" />{{ t('stand.random') }}</button>
    </PageHeader>

    <section class="mx-auto max-w-7xl px-4 sm:px-6">
      <div class="card animate-rise grid gap-3 p-4 sm:p-5 md:grid-cols-[1.6fr_1fr_1fr_auto] md:items-end">
        <div>
          <label class="label" for="q">{{ t('stand.search') }}</label>
          <div class="relative">
            <Search class="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-faint" />
            <input id="q" v-model="query" class="field pl-9" :placeholder="t('stand.searchHint')" />
          </div>
        </div>
        <div>
          <label class="label" for="fac">{{ t('stand.faculty') }}</label>
          <select id="fac" v-model="faculty" class="field">
            <option value="">{{ t('stand.all') }}</option>
            <option v-for="f in meta?.faculties ?? []" :key="f" :value="f">{{ f }}</option>
          </select>
        </div>
        <div>
          <label class="label" for="lvl">{{ t('portfolio.level') }}</label>
          <select id="lvl" v-model="level" class="field">
            <option value="">{{ t('stand.all') }}</option>
            <option v-for="l in ['bachelor', 'master_research', 'master_profile'] as const" :key="l" :value="l">{{ t(`levels.${l}`) }}</option>
          </select>
        </div>
        <label class="flex items-center gap-2 pb-2.5 text-sm text-muted">
          <input v-model="current" type="checkbox" class="h-4 w-4 accent-[var(--primary)]" />{{ t('stand.current') }}
        </label>
      </div>

      <div class="mt-5 flex items-center justify-between text-sm text-muted">
        <p v-if="data">{{ t('stand.found', { n: int(data.total, locale as AppLocale) }) }}</p>
        <div class="flex items-center gap-2">
          <button class="btn-ghost !p-2" :disabled="page === 0" :aria-label="t('stand.prev')" @click="page--"><ChevronLeft class="h-4 w-4" /></button>
          <span class="num">{{ page + 1 }} / {{ pages }}</span>
          <button class="btn-ghost !p-2" :disabled="page + 1 >= pages" :aria-label="t('stand.next')" @click="page++"><ChevronRight class="h-4 w-4" /></button>
        </div>
      </div>

      <div v-if="failed" class="card mt-4 flex items-center gap-3 p-6 text-sm text-bad">
        {{ t('common.loadFailed') }}
        <button class="btn-ghost ml-auto !py-1" @click="load"><RefreshCw class="h-4 w-4" />{{ t('common.retry') }}</button>
      </div>
      <ul v-else-if="data" class="mt-4 grid gap-3 transition-opacity sm:grid-cols-2 lg:grid-cols-3" :class="loading && 'opacity-60'">
        <li v-for="(s, i) in data.items" :key="s.student_id" class="animate-rise" :style="{ animationDelay: `${Math.min(i, 12) * 30}ms` }">
          <RouterLink :to="`/stand/${s.student_id}`" class="card lift flex h-full gap-3 p-4">
            <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary-strong"><UserRound class="h-5 w-5" /></span>
            <div class="min-w-0">
              <p class="font-semibold">{{ t('stand.name', { id: s.student_id.slice(1) }) }}</p>
              <p class="truncate text-sm text-muted" :title="s.program">{{ s.program }}</p>
              <p class="mt-1 text-xs text-faint">{{ t(`levels.${s.level}`) }} · {{ t('stand.intake', { y: s.intake_year }) }}</p>
            </div>
          </RouterLink>
        </li>
      </ul>
      <div v-else class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div v-for="i in 9" :key="i" class="skeleton h-24" />
      </div>
      <p v-if="data && !data.items.length" class="mt-6 text-center text-sm text-faint">{{ t('stand.nothing') }}</p>
    </section>
  </div>
</template>
