<script setup lang="ts">
import { ArrowLeft, BriefcaseBusiness, ClipboardList, GraduationCap, History, RefreshCw, Target, Telescope, Waypoints } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { api } from '../api/client'
import ExplainBars from '../components/ExplainBars.vue'
import RiskMeter from '../components/RiskMeter.vue'
import RulesSwitch from '../components/RulesSwitch.vue'
import TermHint from '../components/TermHint.vue'
import HistoryChart from '../components/stand/HistoryChart.vue'
import { usePortfolio } from '../composables/usePortfolio'
import type { AppLocale, RulesCode, Student } from '../types'
import { num } from '../utils/format'

// карточка студента стенда: история IGPA, прогноз на следующий год (полные модели), проверка прогноза прошлого года
// против факта, записи в АСУ и учёба по годам
const props = defineProps<{ id: string }>()
const { t, locale } = useI18n()
const router = useRouter()
const lang = computed(() => locale.value as AppLocale)
const rules = ref<RulesCode>('default')
const data = ref<Student | null>(null)
const failed = ref(false)
const notFound = ref(false)

async function load() {
  failed.value = false
  notFound.value = false
  try {
    data.value = await api.student(props.id, rules.value, lang.value)
  } catch (e) {
    if ((e as { status?: number }).status === 404) notFound.value = true
    else failed.value = true
  }
}
watch([() => props.id, rules, lang], load, { immediate: true })

const done = computed(() => data.value?.history.filter((h) => h.obs_igpa != null) ?? [])
const last = computed(() => done.value[done.value.length - 1])
const lastYear = computed(() => (last.value ? `${last.value.year}/${(last.value.year + 1) % 100}` : ''))

// проверка: что модели прогнозировали в прошлом году и что случилось
const MODELS = ['B0', 'CatBoost', 'Stack', 'Hybrid']
const backtest = computed(() => {
  const rows = (data.value?.backtest ?? []).filter((r) => MODELS.includes(String(r.model)))
  rows.sort((a, b) => MODELS.indexOf(String(a.model)) - MODELS.indexOf(String(b.model)))
  return rows.map((r) => ({ model: String(r.model), pred: Number(r.pred), y: Number(r.y), err: Math.abs(Number(r.pred) - Number(r.y)) }))
})
const backYear = computed(() => {
  const y = Number(data.value?.backtest[0]?.year)
  return Number.isFinite(y) ? `${y}/${(y + 1) % 100} → ${y + 1}/${(y + 2) % 100}` : ''
})
const maxErr = computed(() => Math.max(...backtest.value.map((r) => r.err), 1e-9))
const backFall = computed(() => {
  const r = data.value?.backtest[0]
  return r ? Number(r.y) <= Number(r.igpa) - 0.1 : false
})

// записи АСУ по годам, новые сверху
const recordsByYear = computed(() => {
  const groups = new Map<number, Student['records']>()
  for (const r of [...(data.value?.records ?? [])].reverse()) groups.set(r.year, [...(groups.get(r.year) ?? []), r])
  return [...groups.entries()]
})
const STATE: Record<string, string> = { Подтверждено: 'approved', Отклонено: 'rejected', 'На согласовании': 'pending', Черновик: 'draft' }
// форма обучения и язык в данных – по-русски, как в АСУ
const FORM: Record<string, string> = { Очная: 'fulltime', Дистанционная: 'distance' }
const LANG: Record<string, string> = { Русский: 'ru', Казахский: 'kk', Английский: 'en' }
const stateCls: Record<string, string> = { approved: 'text-good', rejected: 'text-bad', pending: 'text-accent', draft: 'text-faint' }

// перенести последний завершённый год студента в «Мой портфель»: GPA, прошлый GPA, курс и согласованные записи
const { state: portfolio } = usePortfolio()
function toPortfolio() {
  const d = data.value
  if (!d || !last.value) return
  const prev = done.value[done.value.length - 2]
  const enr = d.enrollment.find((e) => e.year === last.value!.year)
  portfolio.gpa = +(last.value.gpa ?? 0).toFixed(2)
  portfolio.hasPrev = prev?.gpa != null
  portfolio.gpaPrev = +(prev?.gpa ?? 0).toFixed(2)
  portfolio.level = d.student.level
  portfolio.year = enr?.year_of_study ?? 1
  portfolio.rules = rules.value
  portfolio.records = d.records
    .filter((r) => r.year === last.value!.year && r.state === 'Подтверждено')
    .map((r, i) => ({ id: 10_000 + i, category: r.category, status: r.status }))
  router.push('/portfolio')
}
</script>

<template>
  <div class="mx-auto max-w-7xl px-4 pt-24 sm:px-6">
    <RouterLink to="/stand" class="inline-flex items-center gap-1.5 text-sm text-muted hover:text-primary-strong"><ArrowLeft class="h-4 w-4" />{{ t('student.back') }}</RouterLink>

    <div v-if="notFound" class="card mt-6 p-8 text-center text-muted">{{ t('student.notFound') }}</div>
    <div v-else-if="failed" class="card mt-6 flex items-center gap-3 p-6 text-sm text-bad">
      {{ t('common.loadFailed') }}
      <button class="btn-ghost ml-auto !py-1" @click="load"><RefreshCw class="h-4 w-4" />{{ t('common.retry') }}</button>
    </div>
    <template v-else-if="data">
      <header class="mt-4 flex flex-wrap items-end justify-between gap-5 animate-rise">
        <div>
          <p class="eyebrow">{{ data.student.faculty }}</p>
          <h1 class="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">{{ t('stand.name', { id: data.student.student_id.slice(1) }) }}</h1>
          <div class="mt-3 flex flex-wrap gap-2">
            <span class="chip">{{ data.student.program }}</span>
            <span class="chip">{{ t(`levels.${data.student.level}`) }}</span>
            <span class="chip">{{ t('stand.intake', { y: data.student.intake_year }) }}</span>
            <span class="chip">{{ t(`form.${FORM[data.student.form] ?? 'fulltime'}`) }} · {{ t(`langs.${LANG[data.student.language] ?? 'ru'}`) }}</span>
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-3">
          <RulesSwitch v-model="rules" />
          <button v-if="last" v-ripple class="btn-ghost" @click="toPortfolio"><BriefcaseBusiness class="h-4 w-4" />{{ t('student.toPortfolio') }}</button>
        </div>
      </header>

      <!-- последний завершённый год -->
      <dl v-if="last" class="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div v-for="(tile, i) in [
          { k: 'igpa', v: num(last.obs_igpa, lang), cls: '' },
          { k: 'gpa', v: num(last.gpa, lang), cls: 'text-gpa' },
          { k: 'iros', v: num(last.obs_iros, lang, 3), cls: 'text-iros' },
          { k: 'ssci', v: num(last.obs_ssci, lang, 3), cls: 'text-ssci' },
        ]" :key="tile.k" class="card animate-rise p-4" :style="{ animationDelay: `${i * 60}ms` }">
          <dt class="text-xs text-faint">{{ t(`student.tile.${tile.k}`, { y: lastYear }) }}</dt>
          <dd class="num mt-1 text-2xl font-bold" :class="tile.cls">{{ tile.v }}</dd>
        </div>
      </dl>

      <div class="mt-6 grid items-start gap-6 lg:grid-cols-[1.25fr_1fr]">
        <div class="space-y-6">
          <div class="card animate-rise p-6">
            <h2 class="flex items-center gap-2 font-bold"><History class="h-5 w-5 text-primary" />{{ t('student.history') }}</h2>
            <p class="mt-1 text-sm text-muted">{{ t('student.historyLead') }}</p>
            <HistoryChart class="mt-4" :history="data.history" :forecast="data.forecast" />
          </div>

          <div v-if="backtest.length" class="card animate-rise p-6">
            <h2 class="flex items-center gap-2 font-bold"><Target class="h-5 w-5 text-accent" />{{ t('student.backtest', { y: backYear }) }}</h2>
            <p class="mt-1 text-sm text-muted">
              {{ t('student.backtestLead', { y: num(backtest[0].y, lang) }) }}
              <strong>{{ backFall ? t('student.fell') : t('student.notFell') }}</strong>
            </p>
            <ul class="mt-5 space-y-3">
              <li v-for="(r, i) in backtest" :key="r.model" class="grid grid-cols-[6rem_1fr_7.5rem] items-center gap-3 text-sm">
                <span class="font-semibold">{{ r.model }}</span>
                <div class="h-2 overflow-hidden rounded-full bg-surface-2">
                  <div class="grow-x h-full origin-left rounded-full" :class="r.model === 'B0' ? 'bg-faint' : 'bg-primary'" :style="{ width: `${(r.err / maxErr) * 100}%`, animationDelay: `${i * 80}ms` }" />
                </div>
                <span class="num text-right text-muted">{{ num(r.pred, lang) }} <span class="text-faint">±{{ num(r.err, lang) }}</span></span>
              </li>
            </ul>
            <p class="mt-3 text-xs text-faint">{{ t('student.backtestNote') }}</p>
          </div>

          <div class="card animate-rise p-6">
            <h2 class="flex items-center gap-2 font-bold"><ClipboardList class="h-5 w-5 text-accent" />{{ t('student.records', { n: data.records.length }) }}</h2>
            <div v-for="[year, recs] in recordsByYear" :key="year" class="mt-5">
              <p class="eyebrow">{{ year }}/{{ (year + 1) % 100 }}</p>
              <ul class="mt-2 divide-y divide-line">
                <li v-for="(r, i) in recs" :key="i" class="flex items-start gap-3 py-2.5">
                  <span class="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full" :class="r.category.startsWith('IROS') ? 'bg-iros' : 'bg-ssci'" aria-hidden="true" />
                  <div class="min-w-0 flex-1">
                    <p class="text-sm font-medium">{{ r.title }}</p>
                    <p class="text-xs text-faint">{{ r.category_name }} · {{ r.status_name }} · <span class="num">{{ r.event_date }}</span></p>
                  </div>
                  <span class="shrink-0 text-xs font-semibold" :class="stateCls[STATE[r.state] ?? 'draft']">{{ t(`state.${STATE[r.state] ?? 'draft'}`) }}</span>
                </li>
              </ul>
            </div>
            <p v-if="!data.records.length" class="mt-4 text-sm text-faint">{{ t('student.noRecords') }}</p>
          </div>
        </div>

        <div class="space-y-6">
          <div v-if="data.forecast" class="card animate-rise p-6">
            <h2 class="flex items-center gap-2 font-bold"><Telescope class="h-5 w-5 text-primary" />{{ t('student.forecastTitle') }}</h2>
            <div class="mt-4 grid grid-cols-2 gap-4">
              <div>
                <p class="text-xs text-faint">{{ t('forecast.mean') }}</p>
                <p class="text-4xl font-bold tracking-tight">{{ num(data.forecast.pred, lang) }}</p>
              </div>
              <div>
                <p class="flex items-center gap-1 text-xs text-faint">{{ t('forecast.band') }} <TermHint term="band" /></p>
                <p class="num mt-1.5 text-xl font-semibold">{{ num(data.forecast.p10, lang) }} – {{ num(data.forecast.p90, lang) }}</p>
              </div>
            </div>
            <RiskMeter class="mt-5" :risk="data.forecast.risk" />
            <p class="mt-4 text-xs leading-relaxed text-faint">{{ t('student.fullModel') }}</p>
          </div>

          <div v-if="data.forecast" class="card animate-rise p-6">
            <h2 class="flex items-center gap-2 font-bold"><Waypoints class="h-5 w-5 text-primary" />{{ t('explain.title') }} <TermHint term="shap" /></h2>
            <ExplainBars class="mt-5" :factors="data.forecast.factors" />
          </div>

          <div class="card animate-rise p-6">
            <h2 class="flex items-center gap-2 font-bold"><GraduationCap class="h-5 w-5 text-gpa" />{{ t('student.study') }}</h2>
            <table class="mt-4 w-full text-sm">
              <thead>
                <tr class="text-left text-xs text-faint">
                  <th class="pb-2 font-medium">{{ t('student.year') }}</th>
                  <th class="pb-2 font-medium">{{ t('portfolio.year') }}</th>
                  <th class="pb-2 text-right font-medium">GPA</th>
                  <th class="pb-2 pl-3 font-medium">{{ t('student.outcome') }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-line">
                <tr v-for="e in data.enrollment" :key="e.year">
                  <td class="num py-2">{{ e.year }}/{{ (e.year + 1) % 100 }}</td>
                  <td class="num py-2">{{ e.year_of_study }}</td>
                  <td class="num py-2 text-right font-semibold">{{ num(e.gpa_year, lang) }}</td>
                  <td class="py-2 pl-3 text-muted">{{ t(`outcome.${e.outcome}`) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>
    <div v-else class="mt-6 space-y-4">
      <div class="skeleton h-24" />
      <div class="skeleton h-80" />
    </div>
  </div>
</template>
