<script setup lang="ts">
import { ShieldAlert, ShieldCheck, ShieldQuestion } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { AppLocale } from '../types'
import { pct } from '../utils/format'
import TermHint from './TermHint.vue'

// вероятность, что IGPA снизится на 0,1 и больше; уровень всегда с иконкой и подписью, не только цветом.
// Пороги – от доли снижения на стенде (около 17% по Положению): ниже 12% – низкий, от 30% – высокий
const props = defineProps<{ risk: number }>()
const { t, locale } = useI18n()
const level = computed(() => (props.risk < 0.12 ? 'low' : props.risk < 0.3 ? 'mid' : 'high'))
const look = computed(
  () =>
    ({
      low: { icon: ShieldCheck, cls: 'text-good', bar: 'bg-good' },
      mid: { icon: ShieldQuestion, cls: 'text-accent', bar: 'bg-accent' },
      high: { icon: ShieldAlert, cls: 'text-bad', bar: 'bg-bad' },
    })[level.value],
)
</script>

<template>
  <div>
    <div class="flex items-center justify-between gap-3">
      <p class="flex items-center gap-1.5 text-sm font-semibold">{{ t('forecast.risk') }} <TermHint term="risk" /></p>
      <p class="flex items-center gap-1.5 text-sm font-semibold" :class="look.cls">
        <component :is="look.icon" class="h-4 w-4" />{{ t(`forecast.level.${level}`) }}
      </p>
    </div>
    <div class="mt-2 flex items-center gap-3">
      <span class="num text-3xl font-bold">{{ pct(risk, locale as AppLocale) }}</span>
      <div class="h-2 flex-1 overflow-hidden rounded-full bg-surface-2">
        <div class="pour h-full rounded-full" :class="look.bar" :style="{ width: `${Math.min(100, risk * 100)}%` }" />
      </div>
    </div>
  </div>
</template>
