<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { rows, val } from '../../composables/useResearch'
import type { AppLocale, Research } from '../../types'
import { num, pct } from '../../utils/format'
import TermHint from '../TermHint.vue'
import BarList, { type Bar } from './BarList.vue'

// серия S7: те же студенты и записи по трём правилам – сколько разброса IGPA дают достижения; и рекомендатель:
// ожидаемый прирост первого совета при каждой стратегии
const props = defineProps<{ data: Research }>()
const { t, locale } = useI18n()
const lang = computed(() => locale.value as AppLocale)
const RULES = ['default', 'eduscore', 'percentile'] as const

const shares = computed<Bar[]>(() =>
  RULES.map((r) => {
    const row = rows(props.data, 'normalization', { rules: r, layer: 'true' })[0]
    return { key: r, label: t(`rules.${r}`), value: val(row, 'achievement_share') ?? 0, text: pct(val(row, 'achievement_share'), lang.value), cls: 'bg-accent' }
  }),
)
const norm = computed(() => RULES.map((r) => ({ r, row: rows(props.data, 'normalization', { rules: r, layer: 'true' })[0] })))

const STRATEGY: Record<string, string> = {
  'Наша: прирост × реалистичность': 'ours',
  'Только прирост по формуле': 'gainOnly',
  'Самое частое достижение': 'popular',
  'Случайное действие': 'random',
}
const ORDER = ['ours', 'gainOnly', 'popular', 'random']
const strategies = computed(() =>
  ORDER.map((key) => ({
    key,
    cells: RULES.map((r) => val(rows(props.data, 'recommendations', { rules: r }).find((x) => STRATEGY[String(x.strategy)] === key), 'expected')),
  })),
)
const best = computed(() => RULES.map((_, i) => Math.max(...strategies.value.map((s) => s.cells[i] ?? 0))))
const quality = computed(() => rows(props.data, 'feasibility_quality', { rules: 'default' })[0])
</script>

<template>
  <div class="space-y-6">
    <div class="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
      <div class="card p-6">
        <h3 class="flex items-center gap-1.5 font-bold">{{ t('research.shareTitle') }} <TermHint term="achShare" /></h3>
        <p class="mt-1 text-sm text-muted">{{ t('research.shareLead') }}</p>
        <BarList class="mt-5" :bars="shares" :max="1" />
        <p class="mt-4 text-sm leading-relaxed">{{ t('research.shareConclusion') }}</p>
      </div>
      <div class="card overflow-x-auto p-6">
        <h3 class="flex items-center gap-1.5 font-bold">{{ t('research.normTitle') }} <TermHint term="rules" /></h3>
        <table class="mt-4 w-full min-w-[26rem] text-sm">
          <thead>
            <tr class="text-left text-xs text-faint">
              <th class="pb-2 font-medium">{{ t('research.col.rules') }}</th>
              <th class="pb-2 text-right font-medium">{{ t('research.col.iros') }}</th>
              <th class="pb-2 text-right font-medium">{{ t('research.col.ssci') }}</th>
              <th class="pb-2 text-right font-medium">{{ t('research.col.igpa') }}</th>
              <th class="pb-2 text-right font-medium">{{ t('research.col.decline') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-line">
            <tr v-for="n in norm" :key="n.r">
              <td class="py-2 font-semibold">{{ t(`rules.${n.r}`) }}</td>
              <td class="num py-2 text-right text-iros">{{ num(val(n.row, 'iros_mean'), lang, 3) }}</td>
              <td class="num py-2 text-right text-ssci">{{ num(val(n.row, 'ssci_mean'), lang, 3) }}</td>
              <td class="num py-2 text-right">{{ num(val(n.row, 'igpa_mean'), lang) }} ± {{ num(val(n.row, 'igpa_sd'), lang) }}</td>
              <td class="num py-2 text-right">{{ pct(val(n.row, 'risk_share'), lang) }}</td>
            </tr>
          </tbody>
        </table>
        <p class="mt-4 text-xs leading-relaxed text-faint">{{ t('research.normNote') }}</p>
      </div>
    </div>

    <div class="card overflow-x-auto p-6">
      <h3 class="flex items-center gap-1.5 font-bold">{{ t('research.recTitle') }} <TermHint term="expected" /></h3>
      <p class="mt-1 text-sm text-muted">{{ t('research.recLead') }}</p>
      <table class="mt-4 w-full min-w-[34rem] text-sm">
        <thead>
          <tr class="text-left text-xs text-faint">
            <th class="pb-2 font-medium"><span class="inline-flex items-center gap-1">{{ t('research.col.strategy') }} <TermHint term="strategy" /></span></th>
            <th v-for="r in RULES" :key="r" class="pb-2 text-right font-medium">{{ t(`rules.${r}`) }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-line">
          <tr v-for="s in strategies" :key="s.key">
            <td class="py-2" :class="s.key === 'ours' && 'font-semibold text-accent'">{{ t(`strategy.${s.key}`) }}</td>
            <td v-for="(c, i) in s.cells" :key="i" class="num py-2 text-right" :class="c === best[i] && 'font-bold text-good'">{{ num(c, lang, 3) }}</td>
          </tr>
        </tbody>
      </table>
      <p class="mt-4 text-sm leading-relaxed text-muted">
        {{ t('research.recConclusion', { auc: num(val(quality, 'auc_records'), lang), pred: pct(val(quality, 'mean_feasibility'), lang, 1), fact: pct(val(quality, 'observed_rate'), lang, 1) }) }}
      </p>
    </div>
  </div>
</template>
