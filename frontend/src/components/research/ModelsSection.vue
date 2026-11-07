<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { rows, val } from '../../composables/useResearch'
import type { AppLocale, Research } from '../../types'
import { num, pct } from '../../utils/format'
import TermHint from '../TermHint.vue'
import BarList, { type Bar } from './BarList.vue'
import ForestPlot, { type ForestRow } from './ForestPlot.vue'

// модели на последней проверке (2024/25 → 2025/26, 2 492 перехода): MAE с ДИ, выигрыш к B0, ROC-AUC, p по Холму;
// серия S8 – смена правил без переобучения; серии S0–S3 – вклад групп признаков
const props = defineProps<{ data: Research }>()
const { t, locale } = useI18n()
const lang = computed(() => locale.value as AppLocale)
const rules = ref<'default' | 'eduscore'>('default')
const layer = ref<'obs' | 'true'>('obs')

const ORDER = ['B0', 'B1', 'Ridge', 'RF', 'CatBoost', 'Stack', 'Mean', 'Hybrid']
const table = computed(() => {
  const where = { rules: rules.value, layer: layer.value }
  const base = rows(props.data, 'models', where).filter((r) => ORDER.includes(String(r.model)))
  const hybrid = rows(props.data, 'hybrid', where).filter((r) => r.model === 'Hybrid')
  return [...base, ...hybrid].sort((a, b) => ORDER.indexOf(String(a.model)) - ORDER.indexOf(String(b.model)))
})
const forest = computed<ForestRow[]>(() =>
  table.value.map((r) => ({
    key: String(r.model),
    label: t(`models.${r.model}`),
    mae: val(r, 'mae')!,
    lo: val(r, 'mae_lo')!,
    hi: val(r, 'mae_hi')!,
    muted: r.model === 'B0' || r.model === 'B1',
    accent: r.model === 'Hybrid',
  })),
)
const b0 = computed(() => val(table.value.find((r) => r.model === 'B0'), 'mae'))
const p = (v: number | null) => (v == null ? '–' : v < 1e-4 ? `< ${num(0.0001, lang.value, 4)}` : num(v, lang.value, 3))

// S8: правила сменились с A на B, а модели обучены при A
const VARIANT_KEYS: Record<string, string> = {
  'B0 по правилам B': 'b0',
  'CatBoost, обучен при A, как есть': 'catAsIs',
  'CatBoost, обучен при A, перенос изменения': 'catTransfer',
  'Stack, обучен при A, как есть': 'stackAsIs',
  'Stack, обучен при A, перенос изменения': 'stackTransfer',
  'Hybrid, калькулятор по B': 'hybrid',
  'CatBoost, переобучен при B (ориентир)': 'catRetrained',
  'Stack, переобучен при B (ориентир)': 'stackRetrained',
}
const S8_ORDER = Object.values(VARIANT_KEYS)
const s8 = computed<ForestRow[]>(() =>
  rows(props.data, 'rule_change', { layer: layer.value, from: 'default', to: 'eduscore' })
    .map((r) => ({ r, key: VARIANT_KEYS[String(r.variant)] ?? 'other' }))
    .sort((a, b) => S8_ORDER.indexOf(a.key) - S8_ORDER.indexOf(b.key))
    .map(({ r, key }) => ({
      key,
      label: t(`s8.${key}`),
      mae: val(r, 'mae')!,
      lo: val(r, 'mae_lo')!,
      hi: val(r, 'mae_hi')!,
      muted: key === 'b0' || key.endsWith('Retrained'),
      accent: key === 'hybrid',
    })),
)
const s8b0 = computed(() => s8.value.find((r) => r.key === 'b0')?.mae ?? null)

// S0–S3: выигрыш к B0 с разными наборами признаков (параметры CatBoost общие)
const series = computed<Bar[]>(() =>
  rows(props.data, 'series', { rules: rules.value, layer: layer.value })
    .filter((r) => r.model !== 'B0')
    .map((r) => ({
      key: String(r.model),
      label: t(`series.${String(r.model).replace('-', '_')}`),
      value: val(r, 'gain') ?? 0,
      text: pct(val(r, 'gain'), lang.value, 1),
      cls: String(r.model).startsWith('S3') ? 'bg-iros' : 'bg-primary',
    })),
)
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap gap-3">
      <div class="flex rounded-full bg-surface-2 p-1" role="radiogroup">
        <button v-for="r in ['default', 'eduscore'] as const" :key="r" role="radio" :aria-checked="rules === r" class="rounded-full px-3.5 py-1.5 text-sm font-semibold" :class="rules === r ? 'bg-surface text-primary-strong shadow-sm' : 'text-muted'" @click="rules = r">{{ t(`rules.${r}`) }}</button>
      </div>
      <div class="flex rounded-full bg-surface-2 p-1" role="radiogroup">
        <button v-for="l in ['obs', 'true'] as const" :key="l" role="radio" :aria-checked="layer === l" class="rounded-full px-3.5 py-1.5 text-sm font-semibold" :class="layer === l ? 'bg-surface text-primary-strong shadow-sm' : 'text-muted'" @click="layer = l">{{ t(`research.layer.${l}`) }}</button>
      </div>
      <TermHint term="layer" />
    </div>

    <div class="card p-6">
      <h3 class="font-bold">{{ t('research.modelsTitle') }}</h3>
      <p class="mt-1 text-sm text-muted">{{ t('research.modelsLead') }}</p>
      <ForestPlot class="mt-5" :rows="forest" :reference="b0" />
    </div>

    <div class="card overflow-x-auto p-6">
      <table class="w-full min-w-[40rem] text-sm">
        <thead>
          <tr class="text-left text-xs text-faint">
            <th class="pb-2 font-medium"><span class="inline-flex items-center gap-1">{{ t('research.col.model') }} <TermHint term="models" /></span></th>
            <th class="pb-2 text-right font-medium"><span class="inline-flex items-center gap-1">MAE <TermHint term="mae" /></span></th>
            <th class="pb-2 text-right font-medium"><span class="inline-flex items-center gap-1">{{ t('research.col.ci') }} <TermHint term="ci" /></span></th>
            <th class="pb-2 text-right font-medium"><span class="inline-flex items-center gap-1">{{ t('research.col.gain') }} <TermHint term="b0" /></span></th>
            <th class="pb-2 text-right font-medium"><span class="inline-flex items-center gap-1">ROC-AUC <TermHint term="rocauc" /></span></th>
            <th class="pb-2 text-right font-medium"><span class="inline-flex items-center gap-1">p <TermHint term="holm" /></span></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-line">
          <tr v-for="r in table" :key="String(r.model)">
            <td class="py-2 font-semibold" :class="r.model === 'Hybrid' && 'text-accent'">{{ t(`models.${r.model}`) }}</td>
            <td class="num py-2 text-right">{{ num(val(r, 'mae'), lang, 4) }}</td>
            <td class="num py-2 text-right text-muted">{{ num(val(r, 'mae_lo'), lang, 3) }}–{{ num(val(r, 'mae_hi'), lang, 3) }}</td>
            <td class="num py-2 text-right font-semibold" :class="(val(r, 'gain') ?? 0) > 0 && 'text-good'">{{ pct(val(r, 'gain'), lang, 1) }}</td>
            <td class="num py-2 text-right">{{ num(val(r, 'roc_auc'), lang, 3) }}</td>
            <td class="num py-2 text-right text-muted">{{ p(val(r, 'p_holm')) }}</td>
          </tr>
        </tbody>
      </table>
      <p class="mt-4 text-sm leading-relaxed text-muted">{{ t('research.modelsConclusion') }}</p>
    </div>

    <div class="grid gap-6">
      <div class="card p-6">
        <h3 class="flex items-center gap-1.5 font-bold">{{ t('research.s8Title') }} <TermHint term="transfer" /></h3>
        <p class="mt-1 text-sm text-muted">{{ t('research.s8Lead') }}</p>
        <ForestPlot class="mt-5" :rows="s8" :reference="s8b0" wide />
        <p class="mt-3 text-xs text-faint">{{ t('research.s8Note') }}</p>
      </div>
      <div class="card p-6">
        <h3 class="flex items-center gap-1.5 font-bold">{{ t('research.seriesTitle') }} <TermHint term="series" /></h3>
        <p class="mt-1 text-sm text-muted">{{ t('research.seriesLead') }}</p>
        <BarList class="mt-5" :bars="series" />
        <p class="mt-3 text-xs text-faint">{{ t('research.seriesNote') }}</p>
      </div>
    </div>
  </div>
</template>
