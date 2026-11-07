<script setup lang="ts">
import { CalendarClock, Database, FileSpreadsheet, Globe, Layers, ScanLine, Shuffle, Users } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { rows, val } from '../../composables/useResearch'
import type { AppLocale, Research, ResearchRow } from '../../types'
import { num, pct } from '../../utils/format'
import TermHint from '../TermHint.vue'
import LearningChart from './LearningChart.vue'

// семь проверок после основных серий: числа считаются здесь из таблиц research.json, тексты – выводы
const props = defineProps<{ data: Research }>()
const { t, locale } = useI18n()
const lang = computed(() => locale.value as AppLocale)
const gain = (b0: number | null, m: number | null) => (b0 && m != null ? 1 - m / b0 : null)
const mae = (list: ResearchRow[], where: Record<string, unknown>) => val(list.find((r) => Object.entries(where).every(([k, v]) => r[k] === v)), 'mae')

// облегчённые модели сайта: последняя проверка, правила Положения
const light = computed(() => {
  const list = rows(props.data, 'check_light', { rules: 'default', year: 2024 })
  const h = list.find((r) => r.model === 'Hybrid облегчённый')
  return { gain: gain(mae(list, { model: 'B0' }), val(h, 'mae')), coverage: val(h, 'coverage_80'), pred: val(h, 'risk_mean_pred'), fact: val(h, 'risk_observed') }
})

// кривая обучения на версии с 12 000 студентов (или на v1, если её нет)
const learningVersion = ref<'v1-12k' | 'v1'>('v1-12k')
const learning = computed(() => rows(props.data, 'check_learning', { rules: 'default', version: learningVersion.value }))

// только выгрузка АСУ против всех данных; магистранты с одним годом истории
const scenarios = computed(() => {
  const list = rows(props.data, 'check_scenarios', { rules: 'default' })
  const all = mae(list, { scenario: 'все данные', model: 'CatBoost' })
  const exp = mae(list, { scenario: 'только выгрузка АСУ и GPA', model: 'CatBoost' })
  const b0m = mae(list, { scenario: 'магистранты', model: 'B0' })
  const one = mae(list, { scenario: 'магистранты, один год истории', model: 'CatBoost' })
  return { loss: all && exp ? exp / all - 1 : null, masters: gain(b0m, one) }
})

// семестровый горизонт: слой АСУ, оба семестра
const semester = computed(() => {
  const list = rows(props.data, 'check_semester', { layer: 'obs', start: 'all' })
  return { gain: gain(mae(list, { model: 'B0 не изменится' }), mae(list, { model: 'CatBoost' })) }
})

// UCI: лучшая модель против «G3 = G2»
const uci = computed(() =>
  ['математика', 'португальский'].map((subject) => {
    const list = rows(props.data, 'check_open_uci', { subject })
    const b0 = mae(list, { model: 'B0: G3 = G2', features: 'оценки' })
    const models = list.filter((r) => r.model !== 'B0: G3 = G2')
    const best = Math.min(...models.map((r) => Number(r.mae)))
    const withAct = Math.min(...models.filter((r) => r.features === 'оценки и активность').map((r) => Number(r.mae)))
    return { subject, b0, best, withAct }
  }),
)

// устойчивость: выигрыш лучшей модели к B0 на трёх версиях синтетики (Положение, АСУ)
const robust = computed(() =>
  ['v1', 'v1-seed2', 'v1-aitu'].map((version) => {
    const list = rows(props.data, 'robust_models', { version, rules: 'default', layer: 'obs' })
    return { version, gain: Math.max(...list.map((r) => val(r, 'gain') ?? -1)) }
  }),
)

// непересекающиеся студенты: Stack, Положение, АСУ
const disjoint = computed(() => ({
  normal: val(rows(props.data, 'models', { rules: 'default', layer: 'obs', model: 'Stack' })[0], 'gain'),
  disjoint: val(rows(props.data, 'disjoint', { rules: 'default', layer: 'obs', model: 'Stack' })[0], 'gain'),
}))
</script>

<template>
  <div class="space-y-6">
    <p class="max-w-3xl text-sm leading-relaxed text-muted">{{ t('research.relLead') }}</p>
    <div class="grid gap-6 lg:grid-cols-2">
      <div class="card p-6">
        <h3 class="flex items-center gap-2 font-bold"><ScanLine class="h-5 w-5 text-primary" />{{ t('research.rel.light') }}</h3>
        <dl class="mt-4 grid grid-cols-3 gap-3 text-center">
          <div class="rounded-2xl bg-surface-2 p-3"><dt class="text-xs text-faint">{{ t('research.rel.gainB0') }}</dt><dd class="num mt-1 text-xl font-bold">{{ pct(light.gain, lang, 1) }}</dd></div>
          <div class="rounded-2xl bg-surface-2 p-3"><dt class="flex items-center justify-center gap-1 text-xs text-faint">{{ t('research.rel.coverage') }} <TermHint term="band" /></dt><dd class="num mt-1 text-xl font-bold">{{ pct(light.coverage, lang) }}</dd></div>
          <div class="rounded-2xl bg-surface-2 p-3"><dt class="flex items-center justify-center gap-1 text-xs text-faint">{{ t('research.rel.riskCal') }} <TermHint term="calibration" /></dt><dd class="num mt-1 text-xl font-bold">{{ pct(light.pred, lang) }} / {{ pct(light.fact, lang) }}</dd></div>
        </dl>
        <p class="mt-4 text-sm leading-relaxed text-muted">{{ t('research.rel.lightText') }}</p>
      </div>

      <div class="card p-6">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h3 class="flex items-center gap-2 font-bold"><Users class="h-5 w-5 text-primary" />{{ t('research.rel.learning') }} <TermHint term="learning" /></h3>
          <div class="flex rounded-full bg-surface-2 p-0.5 text-xs">
            <button v-for="v in ['v1-12k', 'v1'] as const" :key="v" class="rounded-full px-2.5 py-1 font-semibold" :class="learningVersion === v ? 'bg-surface shadow-sm' : 'text-muted'" @click="learningVersion = v">{{ t(`research.rel.version.${v}`) }}</button>
          </div>
        </div>
        <LearningChart class="mt-3" :rows="learning" />
        <p class="mt-2 text-sm leading-relaxed text-muted">{{ t('research.rel.learningText') }}</p>
      </div>

      <div class="card p-6">
        <h3 class="flex items-center gap-2 font-bold"><FileSpreadsheet class="h-5 w-5 text-primary" />{{ t('research.rel.scenarios') }}</h3>
        <p class="mt-3 text-sm leading-relaxed text-muted">{{ t('research.rel.scenariosText', { loss: pct(scenarios.loss, lang, 1), masters: pct(scenarios.masters, lang) }) }}</p>
      </div>

      <div class="card p-6">
        <h3 class="flex items-center gap-2 font-bold"><CalendarClock class="h-5 w-5 text-primary" />{{ t('research.rel.semester') }}</h3>
        <p class="mt-3 text-sm leading-relaxed text-muted">{{ t('research.rel.semesterText', { gain: pct(semester.gain, lang) }) }}</p>
      </div>

      <div class="card p-6">
        <h3 class="flex items-center gap-2 font-bold"><Globe class="h-5 w-5 text-primary" />{{ t('research.rel.uci') }}</h3>
        <table class="mt-4 w-full text-sm">
          <thead>
            <tr class="text-left text-xs text-faint">
              <th class="pb-2 font-medium">{{ t('research.col.subject') }}</th>
              <th class="pb-2 text-right font-medium">G3 = G2</th>
              <th class="pb-2 text-right font-medium">{{ t('research.col.bestGrades') }}</th>
              <th class="pb-2 text-right font-medium">{{ t('research.col.withActivity') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-line">
            <tr v-for="u in uci" :key="u.subject">
              <td class="py-2">{{ t(`research.rel.subject.${u.subject === 'математика' ? 'math' : 'por'}`) }}</td>
              <td class="num py-2 text-right font-semibold text-good">{{ num(u.b0, lang) }}</td>
              <td class="num py-2 text-right">{{ num(u.best, lang) }}</td>
              <td class="num py-2 text-right">{{ num(u.withAct, lang) }}</td>
            </tr>
          </tbody>
        </table>
        <p class="mt-3 text-sm leading-relaxed text-muted">{{ t('research.rel.uciText') }}</p>
      </div>

      <div class="card p-6">
        <h3 class="flex items-center gap-2 font-bold"><Shuffle class="h-5 w-5 text-primary" />{{ t('research.rel.robust') }}</h3>
        <ul class="mt-4 grid grid-cols-3 gap-3 text-center">
          <li v-for="r in robust" :key="r.version" class="rounded-2xl bg-surface-2 p-3">
            <p class="text-xs text-faint">{{ t(`research.rel.version.${r.version}`) }}</p>
            <p class="num mt-1 text-xl font-bold">{{ pct(r.gain, lang, 1) }}</p>
          </li>
        </ul>
        <p class="mt-3 text-sm leading-relaxed text-muted">{{ t('research.rel.robustText') }}</p>
      </div>

      <div class="card p-6">
        <h3 class="flex items-center gap-2 font-bold"><Layers class="h-5 w-5 text-primary" />{{ t('research.rel.disjoint') }}</h3>
        <p class="mt-3 text-sm leading-relaxed text-muted">{{ t('research.rel.disjointText', { normal: pct(disjoint.normal, lang, 1), disjoint: pct(disjoint.disjoint, lang, 1) }) }}</p>
      </div>

      <div class="card flex items-start gap-3 border-accent/30 bg-accent-soft/40 p-6">
        <Database class="h-5 w-5 shrink-0 text-accent" />
        <p class="text-sm leading-relaxed">{{ t('research.rel.limit') }}</p>
      </div>
    </div>
  </div>
</template>
