<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { AppLocale } from '../types'
import { num } from '../utils/format'
import TermHint from './TermHint.vue'

// ползунок с полем для точного ввода; цвет ползунка – цвет сущности (класс text-gpa и т.п.)
const props = withDefaults(
  defineProps<{ label: string; min: number; max: number; step: number; digits?: number; color?: string; term?: string; hint?: string }>(),
  { digits: 2, color: 'text-primary' },
)
const model = defineModel<number>({ required: true })
const { locale } = useI18n()
const id = `slider-${Math.random().toString(36).slice(2, 8)}`
const shown = computed(() => num(model.value, locale.value as AppLocale, props.digits))

function onInput(event: Event) {
  const raw = (event.target as HTMLInputElement).value.replace(',', '.')
  const value = Number(raw)
  if (raw !== '' && Number.isFinite(value)) model.value = Math.min(props.max, Math.max(props.min, value))
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between gap-3">
      <label :for="id" class="flex items-center gap-1.5 text-sm font-semibold">
        <span class="h-2.5 w-2.5 rounded-full bg-current" :class="color" aria-hidden="true" />
        {{ label }}
        <TermHint v-if="term" :term="term" />
      </label>
      <input
        :value="shown"
        inputmode="decimal"
        class="field num w-24 text-right font-semibold"
        :aria-label="label"
        @change="onInput"
      />
    </div>
    <input
      :id="id"
      v-model.number="model"
      type="range"
      :min="min"
      :max="max"
      :step="step"
      class="mt-2 w-full"
      :class="color"
      :style="{ '--fill': `${((model - min) / (max - min)) * 100}%` }"
    />
    <p v-if="hint" class="mt-1 text-xs text-faint">{{ hint }}</p>
  </div>
</template>
