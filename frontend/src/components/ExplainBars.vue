<script setup lang="ts">
import { ArrowDown, ArrowUp } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { AppLocale, Factor } from '../types'
import { signed } from '../utils/format'

// «Почему такой прогноз»: вклад признаков в прогноз изменения IGPA (SHAP). Вправо – тянет прогноз вверх, влево – вниз;
// направление показано и стрелкой со знаком, не только цветом. Полосы вырастают от нуля
const props = defineProps<{ factors: Factor[] }>()
const { locale } = useI18n()
const lang = computed(() => locale.value as AppLocale)
const max = computed(() => Math.max(...props.factors.map((f) => Math.abs(f.value)), 1e-9))
</script>

<template>
  <ul class="space-y-3">
    <li v-for="(f, i) in factors" :key="f.feature" class="grid grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)_4.2rem] items-center gap-3 text-sm">
      <span class="truncate text-muted" :title="f.name">{{ f.name }}</span>
      <div class="relative h-3">
        <span class="absolute inset-y-[-3px] left-1/2 w-px bg-line" aria-hidden="true" />
        <div
          class="grow-x absolute top-0 h-full"
          :class="f.value >= 0 ? 'left-1/2 origin-left rounded-r-full bg-good' : 'right-1/2 origin-right rounded-l-full bg-bad'"
          :style="{ width: `${(Math.abs(f.value) / max) * 50}%`, animationDelay: `${i * 60}ms` }"
        />
      </div>
      <span class="num flex items-center justify-end gap-0.5 font-semibold" :class="f.value >= 0 ? 'text-good' : 'text-bad'">
        <component :is="f.value >= 0 ? ArrowUp : ArrowDown" class="h-3.5 w-3.5" />{{ signed(f.value, lang, 3) }}
      </span>
    </li>
  </ul>
</template>
