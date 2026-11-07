<script setup lang="ts">
import { GraduationCap } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { MAX_YEAR, usePortfolio } from '../../composables/usePortfolio'
import type { Level } from '../../types'
import NumberSlider from '../NumberSlider.vue'
import TermHint from '../TermHint.vue'

// учёба: GPA этого и прошлого года, уровень и курс (курсов столько, сколько длится программа)
const { t } = useI18n()
const { state } = usePortfolio()
const LEVELS: Level[] = ['bachelor', 'master_research', 'master_profile']
const years = computed(() => Array.from({ length: MAX_YEAR[state.level] }, (_, i) => i + 1))
</script>

<template>
  <div class="card space-y-6 p-6">
    <h2 class="flex items-center gap-2 font-bold"><GraduationCap class="h-5 w-5 text-gpa" />{{ t('portfolio.study') }}</h2>
    <NumberSlider v-model="state.gpa" :label="t('portfolio.gpa')" :min="0" :max="4" :step="0.01" color="text-gpa" term="gpa" />
    <div>
      <label class="flex items-center gap-2 text-sm text-muted">
        <input v-model="state.hasPrev" type="checkbox" class="h-4 w-4 accent-[var(--primary)]" />
        {{ t('portfolio.hasPrev') }}
        <TermHint term="gpaPrev" />
      </label>
      <Transition
        enter-from-class="opacity-0 -translate-y-1"
        leave-to-class="opacity-0 -translate-y-1"
        enter-active-class="transition duration-200"
        leave-active-class="transition duration-150"
      >
        <NumberSlider v-if="state.hasPrev" v-model="state.gpaPrev" class="mt-4" :label="t('portfolio.gpaPrev')" :min="0" :max="4" :step="0.01" color="text-faint" />
      </Transition>
    </div>
    <div class="grid gap-4 sm:grid-cols-[1.4fr_1fr]">
      <div>
        <label class="label" for="level">{{ t('portfolio.level') }}</label>
        <select id="level" v-model="state.level" class="field">
          <option v-for="l in LEVELS" :key="l" :value="l">{{ t(`levels.${l}`) }}</option>
        </select>
      </div>
      <div>
        <span class="label">{{ t('portfolio.year') }}</span>
        <div class="flex gap-1.5" role="radiogroup" :aria-label="t('portfolio.year')">
          <button
            v-for="y in years"
            :key="y"
            role="radio"
            :aria-checked="state.year === y"
            class="num h-9 w-9 rounded-xl border text-sm font-semibold transition-colors"
            :class="state.year === y ? 'border-primary bg-primary text-on-primary' : 'border-line text-muted hover:text-ink'"
            @click="state.year = y"
          >
            {{ y }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
