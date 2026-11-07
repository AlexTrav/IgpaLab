<script setup lang="ts">
import { refDebounced } from '@vueuse/core'
import { Target, TrendingUp } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import FormulaBar from '../components/FormulaBar.vue'
import NumberSlider from '../components/NumberSlider.vue'
import PageHeader from '../components/PageHeader.vue'
import TermHint from '../components/TermHint.vue'
import { useCountUp } from '../composables/useCountUp'
import type { AppLocale } from '../types'
import { num } from '../utils/format'
import { SCALE, gpaForTarget, igpaParts } from '../utils/igpa'

// «Быстрый расчёт»: IGPA по трём числам выгрузки АСУ и обратный расчёт. Правила здесь не нужны – они меняют только
// перевод записей в iROS и SSCI, а сама формула одна. Значения живут в адресе страницы (?gpa=&iros=&ssci=&target=)
const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const lang = computed(() => locale.value as AppLocale)

const fromQuery = (key: string, fallback: number, max: number) => {
  const v = Number(route.query[key])
  return Number.isFinite(v) && route.query[key] !== undefined ? Math.min(max, Math.max(0, v)) : fallback
}
const gpa = ref(fromQuery('gpa', 3.0, SCALE))
const iros = ref(fromQuery('iros', 0.02, 1))
const ssci = ref(fromQuery('ssci', 0.05, 1))
const target = ref(fromQuery('target', 2.0, SCALE))

const settled = refDebounced(computed(() => [gpa.value, iros.value, ssci.value, target.value]), 300)
watch(settled, ([g, i, s, tg]) => {
  router.replace({ query: { gpa: g.toFixed(2), iros: i.toFixed(3), ssci: s.toFixed(3), target: tg.toFixed(2) } })
})

const parts = computed(() => igpaParts(gpa.value, iros.value, ssci.value))
const shown = useCountUp(computed(() => parts.value.igpa), 500)
const need = computed(() => gpaForTarget(target.value, iros.value, ssci.value))

// типичные значения синтетического вуза: средние по Положению на слое АСУ и потолки 95% (правило percentile)
const PRESETS = [
  { key: 'typical', gpa: 3.0, iros: 0.011, ssci: 0.03 },
  { key: 'top5', gpa: 3.4, iros: 0.08, ssci: 0.2 },
  { key: 'max', gpa: 4.0, iros: 1, ssci: 1 },
] as const
function apply(p: (typeof PRESETS)[number]) {
  gpa.value = p.gpa
  iros.value = p.iros
  ssci.value = p.ssci
}

// что даёт шаг +0,1 по каждой части: вес · шаг (для iROS и SSCI – ещё ·4)
const steps = computed(() => [
  { key: 'gpa', gain: igpaParts(Math.min(SCALE, gpa.value + 0.1), iros.value, ssci.value).igpa - parts.value.igpa, cls: 'text-gpa' },
  { key: 'iros', gain: igpaParts(gpa.value, Math.min(1, iros.value + 0.1), ssci.value).igpa - parts.value.igpa, cls: 'text-iros' },
  { key: 'ssci', gain: igpaParts(gpa.value, iros.value, Math.min(1, ssci.value + 0.1)).igpa - parts.value.igpa, cls: 'text-ssci' },
])
</script>

<template>
  <div>
    <PageHeader :eyebrow="t('nav.quick')" :title="t('quick.title')" :lead="t('quick.lead')" />
    <section class="mx-auto grid max-w-7xl gap-6 px-4 sm:px-6 lg:grid-cols-[1fr_1.1fr]">
      <div class="card animate-rise space-y-7 self-start p-6 sm:p-7">
        <NumberSlider v-model="gpa" :label="t('parts.gpa')" :min="0" :max="4" :step="0.01" color="text-gpa" term="gpa" :hint="t('quick.gpaHint')" />
        <NumberSlider v-model="iros" :label="t('parts.iros')" :min="0" :max="1" :step="0.005" :digits="3" color="text-iros" term="iros" :hint="t('quick.irosHint')" />
        <NumberSlider v-model="ssci" :label="t('parts.ssci')" :min="0" :max="1" :step="0.005" :digits="3" color="text-ssci" term="ssci" :hint="t('quick.ssciHint')" />
        <div>
          <p class="label">{{ t('quick.presets') }}</p>
          <div class="flex flex-wrap gap-2">
            <button v-for="p in PRESETS" :key="p.key" v-ripple class="btn-ghost !py-1.5" @click="apply(p)">{{ t(`quick.preset.${p.key}`) }}</button>
          </div>
        </div>
      </div>

      <div class="space-y-6">
        <div class="card animate-rise p-6 [animation-delay:80ms] sm:p-7">
          <p class="eyebrow flex items-center gap-1.5">IGPA <TermHint term="igpa" /></p>
          <p class="mt-2 text-6xl leading-none font-bold tracking-tight whitespace-nowrap">
            {{ num(shown, lang) }}<span class="ml-1 text-2xl font-semibold text-faint">/ 4</span>
          </p>
          <FormulaBar class="mt-6" :gpa="parts.gpa" :iros="parts.iros" :ssci="parts.ssci" />
          <dl class="mt-5 grid grid-cols-3 gap-3">
            <div v-for="k in ['gpa', 'iros', 'ssci'] as const" :key="k" class="rounded-2xl bg-surface-2 px-3 py-2.5">
              <dt class="text-xs font-semibold text-muted">{{ t(`parts.${k}`) }}</dt>
              <dd class="num mt-0.5 text-lg font-bold" :class="`text-${k}`">{{ num(parts[k], lang) }}</dd>
            </div>
          </dl>
          <div class="mt-6 border-t border-line pt-5">
            <p class="flex items-center gap-2 text-sm font-semibold"><TrendingUp class="h-4 w-4 text-accent" />{{ t('quick.stepTitle') }} <TermHint term="scale" /></p>
            <ul class="mt-3 grid grid-cols-3 gap-3 text-sm">
              <li v-for="s in steps" :key="s.key">
                <span class="text-muted">{{ t(`parts.${s.key}`) }} +{{ num(0.1, lang, 1) }}</span>
                <span class="num block text-lg font-bold" :class="s.cls">+{{ num(s.gain, lang, 3) }}</span>
              </li>
            </ul>
            <p class="mt-2 text-xs leading-relaxed text-faint">{{ t('quick.stepNote') }}</p>
          </div>
        </div>

        <div class="card animate-rise p-6 [animation-delay:160ms] sm:p-7">
          <p class="flex items-center gap-2 text-sm font-semibold"><Target class="h-4 w-4 text-primary" />{{ t('quick.targetTitle') }} <TermHint term="target" /></p>
          <NumberSlider v-model="target" class="mt-4" :label="t('quick.target')" :min="0" :max="4" :step="0.05" />
          <p class="mt-4 rounded-2xl px-4 py-3 text-sm leading-relaxed" :class="need == null ? 'bg-accent-soft text-ink' : 'bg-primary-soft text-ink'">
            <template v-if="need == null">{{ t('quick.unreachable', { max: num(igpaParts(4, iros, ssci).igpa, lang) }) }}</template>
            <template v-else-if="need === 0">{{ t('quick.already') }}</template>
            <template v-else>
              {{ t('quick.needGpa', { gpa: num(need, lang) }) }}
              <strong v-if="need > gpa">{{ t('quick.needMore', { delta: num(need - gpa, lang) }) }}</strong>
              <strong v-else>{{ t('quick.enough') }}</strong>
            </template>
          </p>
        </div>
      </div>
    </section>
  </div>
</template>
