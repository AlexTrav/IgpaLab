<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { AppLocale } from '../../types'
import { num } from '../../utils/format'

// «лесной» график: MAE каждой модели точкой и 95% доверительный интервал отрезком; вертикаль – уровень B0.
// Меньше – лучше. Подпись значения – справа, текстом, а не цветом
export interface ForestRow {
  key: string
  label: string
  mae: number
  lo: number
  hi: number
  muted?: boolean
  accent?: boolean
}
const props = defineProps<{ rows: ForestRow[]; reference?: number | null; wide?: boolean }>()
const { t, locale } = useI18n()
const lang = computed(() => locale.value as AppLocale)
const scale = computed(() => {
  const lo = Math.min(...props.rows.map((r) => r.lo))
  const hi = Math.max(...props.rows.map((r) => r.hi))
  const pad = (hi - lo) * 0.08 || 0.01
  return { lo: lo - pad, hi: hi + pad }
})
const x = (v: number) => `${((v - scale.value.lo) / (scale.value.hi - scale.value.lo)) * 100}%`
</script>

<template>
  <div>
    <ul class="space-y-2.5" role="list">
      <li
        v-for="(r, i) in rows"
        :key="r.key"
        class="grid items-center gap-3 text-sm"
        :class="wide ? 'grid-cols-[9rem_1fr_4rem] sm:grid-cols-[15rem_1fr_4.5rem]' : 'grid-cols-[7rem_1fr_5.5rem] sm:grid-cols-[9rem_1fr_6.5rem]'"
      >
        <span class="font-semibold" :class="[wide ? 'text-xs leading-snug sm:text-sm' : 'truncate', r.muted ? 'text-faint' : r.accent ? 'text-accent' : '']">{{ r.label }}</span>
        <div class="relative h-6">
          <span v-if="reference != null" class="absolute inset-y-[-6px] w-px border-l border-dashed border-faint" :style="{ left: x(reference) }" aria-hidden="true" />
          <span
            class="grow-x absolute top-1/2 h-1 origin-left -translate-y-1/2 rounded-full"
            :class="r.muted ? 'bg-line' : r.accent ? 'bg-accent/50' : 'bg-primary/40'"
            :style="{ left: x(r.lo), width: `calc(${x(r.hi)} - ${x(r.lo)})`, animationDelay: `${i * 50}ms` }"
          />
          <span
            class="absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface"
            :class="r.muted ? 'bg-faint' : r.accent ? 'bg-accent' : 'bg-primary'"
            :style="{ left: x(r.mae) }"
          />
        </div>
        <span class="num text-right text-muted">{{ num(r.mae, lang, wide ? 3 : 4) }}</span>
      </li>
    </ul>
    <p class="mt-3 text-xs text-faint">{{ t('research.forestNote') }}</p>
  </div>
</template>
