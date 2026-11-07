<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { RulesCode } from '../types'
import TermHint from './TermHint.vue'

// переключатель правила расчёта: Положение, EduScore, «лучшие 5% = 100%» (в коде – percentile)
const model = defineModel<RulesCode>({ required: true })
const { t } = useI18n()
const RULES: RulesCode[] = ['default', 'eduscore', 'percentile']
</script>

<template>
  <div class="flex items-center gap-2">
    <div class="flex flex-wrap rounded-full bg-surface-2 p-1" role="radiogroup" :aria-label="t('formula.rules')">
      <button
        v-for="r in RULES"
        :key="r"
        role="radio"
        :aria-checked="model === r"
        class="rounded-full px-3.5 py-1.5 text-sm font-semibold transition-colors"
        :class="model === r ? 'bg-surface text-primary-strong shadow-sm' : 'text-muted hover:text-ink'"
        @click="model = r"
      >
        {{ t(`rules.${r}`) }}
      </button>
    </div>
    <TermHint term="rules" />
  </div>
</template>
