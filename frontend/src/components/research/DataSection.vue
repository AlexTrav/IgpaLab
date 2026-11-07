<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { rows, val } from '../../composables/useResearch'
import type { AppLocale, Research } from '../../types'
import { num, pct, signed } from '../../utils/format'
import TermHint from '../TermHint.vue'
import BarList, { type Bar } from './BarList.vue'

// данные стенда: участие в АСУ против реального исследования AITU, глобальная важность признаков (SHAP)
// и проверка, что модель «увидела» эффекты, заложенные в генератор
const props = defineProps<{ data: Research }>()
const { t, locale } = useI18n()
const lang = computed(() => locale.value as AppLocale)

// доли студентов хотя бы с одной записью в АСУ; AITU – Soltan и др., 2025
const participation = computed(() => [
  ...['v1', 'v1-seed2', 'v1-aitu'].map((version) => {
    const r = rows(props.data, 'robust_data', { version })[0]
    return { key: version, iros: val(r, 'iros_ever'), ssci: val(r, 'ssci_ever') }
  }),
  { key: 'aitu', iros: 0.26, ssci: 0.7 },
])

const shap = computed<Bar[]>(() => {
  const list = rows(props.data, 'shap', { rules: 'default', task: 'delta' }).sort((a, b) => Number(b.mean_abs_shap) - Number(a.mean_abs_shap)).slice(0, 10)
  return list.map((r) => ({
    key: String(r.feature),
    label: props.data.names[String(r.feature)] ?? String(r.feature),
    value: val(r, 'mean_abs_shap') ?? 0,
    text: num(val(r, 'mean_abs_shap'), lang.value, 4),
    cls: 'bg-primary',
  }))
})

// эффекты генератора: SHAP научных достижений у сильных студентов и перегрузки разовыми SSCI
const EFFECT: Record<string, string> = { 'научные достижения → GPA (у сильных)': 'research', 'перегрузка разовыми SSCI → GPA': 'overload' }
const recovery = computed(() => {
  const list = rows(props.data, 'recovery')
  return Object.entries(EFFECT).map(([name, key]) => ({ key, groups: list.filter((r) => r.effect === name).map((r) => ({ n: val(r, 'n'), shap: val(r, 'mean_shap') })) }))
})
</script>

<template>
  <div class="space-y-6">
    <div class="grid gap-6 lg:grid-cols-2">
      <div class="card p-6">
        <h3 class="font-bold">{{ t('research.dataTitle') }}</h3>
        <ul class="mt-4 space-y-3 text-sm leading-relaxed text-muted">
          <li v-for="k in ['students', 'layers', 'asu', 'real'] as const" :key="k" class="flex gap-3">
            <span class="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" aria-hidden="true" />{{ t(`research.data.${k}`) }}
          </li>
        </ul>
      </div>
      <div class="card overflow-x-auto p-6">
        <h3 class="flex items-center gap-1.5 font-bold">{{ t('research.partTitle') }} <TermHint term="participation" /></h3>
        <p class="mt-1 text-sm text-muted">{{ t('research.partLead') }}</p>
        <table class="mt-4 w-full text-sm">
          <thead>
            <tr class="text-left text-xs text-faint">
              <th class="pb-2 font-medium">{{ t('research.col.version') }}</th>
              <th class="pb-2 text-right font-medium">iROS</th>
              <th class="pb-2 text-right font-medium">SSCI</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-line">
            <tr v-for="p in participation" :key="p.key">
              <td class="py-2" :class="p.key === 'aitu' && 'font-semibold text-accent'">{{ t(`research.rel.version.${p.key}`) }}</td>
              <td class="num py-2 text-right text-iros">{{ pct(p.iros, lang) }}</td>
              <td class="num py-2 text-right text-ssci">{{ pct(p.ssci, lang) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
      <div class="card p-6">
        <h3 class="flex items-center gap-1.5 font-bold">{{ t('research.shapTitle') }} <TermHint term="shap" /></h3>
        <p class="mt-1 text-sm text-muted">{{ t('research.shapLead') }}</p>
        <BarList class="mt-5" :bars="shap" />
      </div>
      <div class="card p-6">
        <h3 class="flex items-center gap-1.5 font-bold">{{ t('research.recoveryTitle') }} <TermHint term="recovery" /></h3>
        <p class="mt-1 text-sm text-muted">{{ t('research.recoveryLead') }}</p>
        <div v-for="e in recovery" :key="e.key" class="mt-5">
          <p class="text-sm font-semibold">{{ t(`research.recovery.${e.key}`) }}</p>
          <div class="mt-2 grid grid-cols-2 gap-3">
            <div v-for="(g, i) in e.groups" :key="i" class="rounded-2xl bg-surface-2 p-3">
              <p class="text-xs text-faint">{{ t(`research.recovery.${e.key}Group${i}`) }} · n = {{ g.n }}</p>
              <p class="num mt-1 text-lg font-bold" :class="Math.abs(g.shap ?? 0) < 5e-5 ? 'text-muted' : (g.shap ?? 0) > 0 ? 'text-good' : 'text-bad'">
                {{ Math.abs(g.shap ?? 0) < 5e-5 ? num(0, lang, 4) : signed(g.shap, lang, 4) }}
              </p>
            </div>
          </div>
        </div>
        <p class="mt-4 text-sm leading-relaxed text-muted">{{ t('research.recoveryText') }}</p>
      </div>
    </div>
  </div>
</template>
