<script setup lang="ts">
import { BookOpenCheck, Check, Plus } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMeta } from '../../composables/useMeta'
import type { Advice, AppLocale } from '../../types'
import { num, pct } from '../../utils/format'
import TermHint from '../TermHint.vue'

// три совета: точный прирост IGPA по калькулятору и реалистичность – как часто похожие студенты этого добиваются;
// советы с достижением можно сразу добавить в портфель, с GPA – применить
const props = defineProps<{ advice: Advice[] }>()
const emit = defineEmits<{ addRecord: [category: string, status: string]; raiseGpa: [step: number] }>()
const { t, locale } = useI18n()
const { categories, statuses } = useMeta()
const lang = computed(() => locale.value as AppLocale)

function title(a: Advice) {
  if (a.kind === 'gpa') return t('advice.gpa', { step: num(a.gpa_step, lang.value, 1) })
  return categories.value.get(a.category!)?.name ?? a.category!
}
function apply(a: Advice) {
  if (a.kind === 'gpa') emit('raiseGpa', a.gpa_step!)
  else emit('addRecord', a.category!, a.status!)
}
const best = computed(() => Math.max(...props.advice.map((a) => a.expected), 1e-9))
</script>

<template>
  <ol class="space-y-3">
    <li
      v-for="(a, i) in advice"
      :key="`${a.kind}:${a.category}:${a.status}:${a.gpa_step}`"
      class="animate-rise rounded-2xl border border-line p-4"
      :style="{ animationDelay: `${i * 90}ms` }"
    >
      <div class="flex items-start gap-3">
        <span
          class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl"
          :class="a.kind === 'gpa' ? 'bg-primary-soft text-gpa' : a.category?.startsWith('IROS') ? 'bg-surface-2 text-iros' : 'bg-surface-2 text-ssci'"
        >
          <BookOpenCheck v-if="a.kind === 'gpa'" class="h-4.5 w-4.5" />
          <Plus v-else class="h-4.5 w-4.5" />
        </span>
        <div class="min-w-0 flex-1">
          <p class="text-sm leading-snug font-semibold">{{ title(a) }}</p>
          <p v-if="a.kind === 'record'" class="text-xs text-faint">{{ statuses.get(a.status!)?.name ?? a.status }}</p>
          <dl class="mt-3 grid grid-cols-3 gap-2 text-xs">
            <div>
              <dt class="text-faint">{{ t('advice.gain') }}</dt>
              <dd class="num text-base font-bold text-good">+{{ num(a.gain, lang, 3) }}</dd>
            </div>
            <div>
              <dt class="text-faint">{{ t('advice.after') }}</dt>
              <dd class="num text-base font-bold">{{ num(a.igpa_after, lang) }}</dd>
            </div>
            <div>
              <dt class="flex items-center gap-1 text-faint">{{ t('advice.feasibility') }} <TermHint term="feasibility" /></dt>
              <dd class="num text-base font-bold">{{ pct(a.feasibility, lang) }}</dd>
            </div>
          </dl>
          <div class="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-2" :title="t('advice.expected')">
            <div class="grow-x h-full origin-left rounded-full bg-accent" :style="{ width: `${(a.expected / best) * 100}%`, animationDelay: `${i * 90 + 200}ms` }" />
          </div>
          <p class="mt-1 flex items-center gap-1 text-[11px] text-faint">{{ t('advice.expectedValue', { v: num(a.expected, lang, 3) }) }} <TermHint term="expected" /></p>
        </div>
      </div>
      <button v-ripple class="btn-ghost mt-3 w-full justify-center !py-1.5" @click="apply(a)">
        <Check class="h-4 w-4" />{{ a.kind === 'gpa' ? t('advice.applyGpa') : t('advice.applyRecord') }}
      </button>
    </li>
  </ol>
</template>
