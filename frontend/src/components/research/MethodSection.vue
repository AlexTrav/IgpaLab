<script setup lang="ts">
import { CircleHelp } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

// методика проверки, честные ограничения и допущения расчёта IGPA, которые ещё нужно подтвердить, – текстом,
// без чисел из данных
const { t } = useI18n()
const STEPS = ['split', 'targets', 'baselines', 'models', 'stats', 'layers'] as const
const LIMITS = ['synthetic', 'additive', 'oneUni', 'rules', 'firstYear'] as const
const ASSUMPTIONS = ['norm', 'scale', 'top5', 'newTypes', 'ssciMix', 'approved', 'period'] as const
</script>

<template>
  <div class="grid gap-6 lg:grid-cols-2">
    <div class="card p-6">
      <h3 class="font-bold">{{ t('research.methodTitle') }}</h3>
      <ol class="mt-4 space-y-4">
        <li v-for="s in STEPS" :key="s" class="relative pl-5">
          <span class="absolute top-1 bottom-1 left-0 w-1 rounded-full bg-primary/60" aria-hidden="true" />
          <p class="text-sm font-semibold">{{ t(`research.method.${s}Title`) }}</p>
          <p class="mt-1 text-sm leading-relaxed text-muted">{{ t(`research.method.${s}`) }}</p>
        </li>
      </ol>
    </div>
    <div class="card p-6">
      <h3 class="font-bold">{{ t('research.limitsTitle') }}</h3>
      <ul class="mt-4 space-y-4">
        <li v-for="l in LIMITS" :key="l" class="relative pl-5">
          <span class="absolute top-1 bottom-1 left-0 w-1 rounded-full bg-accent" aria-hidden="true" />
          <p class="text-sm font-semibold">{{ t(`research.limits.${l}Title`) }}</p>
          <p class="mt-1 text-sm leading-relaxed text-muted">{{ t(`research.limits.${l}`) }}</p>
        </li>
      </ul>
    </div>
    <div class="card p-6 lg:col-span-2">
      <h3 class="flex items-center gap-2 font-bold"><CircleHelp class="h-5 w-5 text-accent" />{{ t('research.assumptionsTitle') }}</h3>
      <p class="mt-1 text-sm text-muted">{{ t('research.assumptionsLead') }}</p>
      <ul class="mt-4 grid gap-4 md:grid-cols-2">
        <li v-for="a in ASSUMPTIONS" :key="a" class="rounded-2xl bg-surface-2 p-4">
          <p class="text-sm font-semibold">{{ t(`research.assumptions.${a}Title`) }}</p>
          <p class="mt-1 text-sm leading-relaxed text-muted">{{ t(`research.assumptions.${a}`) }}</p>
          <p class="mt-2 text-xs leading-relaxed text-faint">{{ t(`research.assumptions.${a}Ask`) }}</p>
        </li>
      </ul>
    </div>
  </div>
</template>
