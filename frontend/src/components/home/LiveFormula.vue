<script setup lang="ts">
import { useIntervalFn } from '@vueuse/core'
import { RefreshCw } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../../api/client'
import { useCountUp } from '../../composables/useCountUp'
import type { AppLocale, Calc, RulesCode } from '../../types'
import { num } from '../../utils/format'
import { WEIGHTS } from '../../utils/igpa'
import { SAMPLES, type Sample } from '../../utils/samples'
import FormulaBar from '../FormulaBar.vue'

// «живая формула» первого экрана: три примера портфеля по очереди, IGPA каждого – калькулятором API по трём
// правилам. Видно главное: по Положению достижения почти не двигают IGPA, по EduScore и с потолком – заметно
const { t, locale } = useI18n()
const RULES: RulesCode[] = ['default', 'eduscore', 'percentile']
const results = ref<Record<string, Calc> | null>(null)
const failed = ref(false)
const sample = ref<Sample['key']>('activist')
const rules = ref<RulesCode>('default')
const touched = ref(false)

async function load() {
  failed.value = false
  try {
    const lang = locale.value as AppLocale
    const pairs = await Promise.all(
      SAMPLES.flatMap((s) => RULES.map(async (r) => [`${s.key}:${r}`, await api.calc(s.gpa, s.records, r, lang)] as const)),
    )
    results.value = Object.fromEntries(pairs)
  } catch {
    failed.value = true
  }
}
onMounted(load)

// примеры сменяются сами, пока человек не выбрал вручную; при «уменьшить движение» – не сменяются
const reduce = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
const { pause } = useIntervalFn(() => {
  const i = SAMPLES.findIndex((s) => s.key === sample.value)
  sample.value = SAMPLES[(i + 1) % SAMPLES.length].key
}, 6500, { immediate: !reduce })
watch(touched, (v) => v && pause())

function pick(key: Sample['key']) {
  touched.value = true
  sample.value = key
}
function pickRules(code: RulesCode) {
  touched.value = true
  rules.value = code
}

const current = computed(() => results.value?.[`${sample.value}:${rules.value}`] ?? null)
const currentSample = computed(() => SAMPLES.find((s) => s.key === sample.value)!)
const igpa = useCountUp(computed(() => current.value?.igpa ?? null), 900)
const lang = computed(() => locale.value as AppLocale)
const formulaLine = computed(
  () => `${num(WEIGHTS.gpa, lang.value, 1)} · GPA + ${num(WEIGHTS.iros, lang.value)} · iROS·4 + ${num(WEIGHTS.ssci, lang.value)} · SSCI·4`,
)
const share = computed(() => {
  const c = current.value
  return c && c.igpa > 0 ? (c.iros_part + c.ssci_part) / c.igpa : 0
})
const terms = computed(() => {
  const c = current.value
  if (!c) return []
  return [
    { key: 'gpa', weight: num(WEIGHTS.gpa, lang.value, 1), value: c.gpa, part: c.gpa_part, cls: 'text-gpa', dot: 'bg-gpa' },
    { key: 'iros', weight: num(WEIGHTS.iros, lang.value), value: c.iros, part: c.iros_part, cls: 'text-iros', dot: 'bg-iros' },
    { key: 'ssci', weight: num(WEIGHTS.ssci, lang.value), value: c.ssci, part: c.ssci_part, cls: 'text-ssci', dot: 'bg-ssci' },
  ]
})
</script>

<template>
  <div class="card relative overflow-hidden p-5 sm:p-7">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="eyebrow">{{ t('formula.title') }}</p>
      <div class="flex flex-wrap gap-1.5" role="group" :aria-label="t('formula.samples')">
        <button
          v-for="s in SAMPLES"
          :key="s.key"
          v-ripple
          class="rounded-full border px-3 py-1 text-xs font-semibold transition-colors"
          :class="sample === s.key ? 'border-primary bg-primary-soft text-primary-strong' : 'border-line text-muted hover:text-ink'"
          :aria-pressed="sample === s.key"
          @click="pick(s.key)"
        >
          {{ t(`samples.${s.key}`) }}
        </button>
      </div>
    </div>

    <p class="mt-3 min-h-10 text-sm text-muted">
      {{ t(`samples.${sample}Note`, { gpa: num(currentSample.gpa, lang), n: currentSample.records.length }) }}
    </p>

    <!-- формула с подставленными числами: вес · значение = вклад -->
    <div class="mt-4 grid grid-cols-[auto_1fr] items-baseline gap-x-3 gap-y-1">
      <span class="text-sm font-semibold text-faint">IGPA =</span>
      <span class="text-sm text-faint">{{ formulaLine }}</span>
    </div>
    <div v-if="current" class="mt-4 grid grid-cols-3 gap-2 sm:gap-3">
      <div v-for="term in terms" :key="term.key" class="rounded-2xl bg-surface-2 px-3 py-3">
        <p class="flex items-center gap-1.5 text-xs font-semibold text-muted">
          <span class="h-2 w-2 rounded-full" :class="term.dot" aria-hidden="true" />
          {{ t(`parts.${term.key}`) }}
        </p>
        <p class="num mt-1 text-lg font-bold sm:text-xl" :class="term.cls">{{ num(term.part, lang) }}</p>
        <p class="num text-[11px] text-faint">
          {{ term.weight }} · {{ term.key === 'gpa' ? num(term.value, lang) : `${num(term.value, lang, 3)}·4` }}
        </p>
      </div>
    </div>
    <div v-else-if="!failed" class="mt-4 grid grid-cols-3 gap-3">
      <div v-for="i in 3" :key="i" class="skeleton h-[86px]" />
    </div>

    <div class="mt-6 flex items-end justify-between gap-4">
      <div>
        <p class="text-xs font-semibold text-faint">IGPA</p>
        <p class="text-5xl leading-none font-bold tracking-tight whitespace-nowrap sm:text-6xl">
          <template v-if="igpa != null">{{ num(igpa, lang) }}</template>
          <span v-else class="skeleton inline-block h-12 w-32 align-middle" />
          <span class="ml-1 text-xl font-semibold text-faint">/ 4</span>
        </p>
      </div>
      <p v-if="current" class="max-w-[13rem] text-right text-xs leading-snug text-muted">
        {{ t('formula.share', { share: num(share * 100, lang, 1) }) }}
      </p>
    </div>
    <FormulaBar class="mt-4" :gpa="current?.gpa_part ?? 0" :iros="current?.iros_part ?? 0" :ssci="current?.ssci_part ?? 0" />

    <!-- те же записи по трём правилам: переключатель и мини-полосы для сравнения -->
    <div class="mt-6 space-y-2.5" role="radiogroup" :aria-label="t('formula.rules')">
      <button
        v-for="r in RULES"
        :key="r"
        role="radio"
        :aria-checked="rules === r"
        class="grid w-full grid-cols-[7.5rem_1fr_3rem] items-center gap-3 rounded-xl px-2 py-1.5 text-left transition-colors sm:grid-cols-[10rem_1fr_3.5rem]"
        :class="rules === r ? 'bg-primary-soft' : 'hover:bg-surface-2'"
        @click="pickRules(r)"
      >
        <span class="truncate text-xs font-semibold" :class="rules === r ? 'text-primary-strong' : 'text-muted'">
          {{ t(`rules.${r}`) }}
        </span>
        <FormulaBar
          :gpa="results?.[`${sample}:${r}`]?.gpa_part ?? 0"
          :iros="results?.[`${sample}:${r}`]?.iros_part ?? 0"
          :ssci="results?.[`${sample}:${r}`]?.ssci_part ?? 0"
          :ticks="false"
          thin
        />
        <span class="num text-right text-sm font-semibold">{{ num(results?.[`${sample}:${r}`]?.igpa, lang) }}</span>
      </button>
    </div>
    <p class="mt-3 text-xs leading-relaxed text-faint">{{ t(`rules.${rules}Note`) }}</p>

    <div v-if="failed" class="mt-4 flex items-center gap-3 rounded-2xl border border-bad/30 px-4 py-3 text-sm text-bad">
      {{ t('common.loadFailed') }}
      <button class="btn-ghost ml-auto !py-1" @click="load"><RefreshCw class="h-4 w-4" />{{ t('common.retry') }}</button>
    </div>
  </div>
</template>
