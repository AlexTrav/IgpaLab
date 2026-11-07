<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCountUp } from '../../composables/useCountUp'
import type { AppLocale, Calc } from '../../types'
import { num } from '../../utils/format'
import FormulaBar from '../FormulaBar.vue'
import TermHint from '../TermHint.vue'

// IGPA сейчас: число, полоса формулы и вклад каждого засчитанного типа достижений
const props = defineProps<{ now: Calc }>()
const { t, locale } = useI18n()
const lang = computed(() => locale.value as AppLocale)
const shown = useCountUp(computed(() => props.now.igpa), 700)
const top = computed(() => [...props.now.categories].filter((c) => c.contribution > 0).sort((a, b) => b.contribution - a.contribution))
// вклад типа в IGPA: доля направления · вес · 4
const toIgpa = (c: Calc['categories'][number]) => c.contribution * (c.profile === 'IROS' ? 0.35 : 0.15) * 4
const maxTop = computed(() => Math.max(...top.value.map(toIgpa), 1e-9))
</script>

<template>
  <div class="card p-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <p class="eyebrow flex items-center gap-1.5">{{ t('portfolio.now') }} <TermHint term="igpa" /></p>
        <p class="mt-2 text-6xl leading-none font-bold tracking-tight whitespace-nowrap">
          {{ num(shown, lang) }}<span class="ml-1 text-2xl font-semibold text-faint">/ 4</span>
        </p>
      </div>
      <span class="chip">{{ t(`rules.${now.rules}`) }}</span>
    </div>
    <FormulaBar class="mt-6" :gpa="now.gpa_part" :iros="now.iros_part" :ssci="now.ssci_part" />
    <dl class="mt-5 grid grid-cols-3 gap-3">
      <div v-for="k in ['gpa', 'iros', 'ssci'] as const" :key="k" class="rounded-2xl bg-surface-2 px-3 py-2.5">
        <dt class="flex items-center gap-1 text-xs font-semibold text-muted">{{ t(`parts.${k}`) }} <TermHint :term="k" /></dt>
        <dd class="num mt-0.5 text-lg font-bold" :class="`text-${k}`">{{ num(now[`${k}_part`], lang) }}</dd>
        <dd v-if="k !== 'gpa'" class="num text-[11px] text-faint">{{ t('portfolio.share', { v: num(now[k], lang, 3) }) }}</dd>
      </div>
    </dl>
    <div v-if="top.length" class="mt-6 border-t border-line pt-5">
      <p class="text-sm font-semibold">{{ t('portfolio.byType') }}</p>
      <ul class="mt-3 space-y-2.5">
        <li v-for="c in top" :key="c.code" class="grid grid-cols-[1fr_4.5rem] items-center gap-3 text-sm">
          <div class="min-w-0">
            <p class="truncate text-muted">{{ c.name }}</p>
            <div class="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-2">
              <div class="pour h-full rounded-full" :class="c.profile === 'IROS' ? 'bg-iros' : 'bg-ssci'" :style="{ width: `${(toIgpa(c) / maxTop) * 100}%` }" />
            </div>
          </div>
          <span class="num text-right font-semibold">+{{ num(toIgpa(c), lang, 3) }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>
