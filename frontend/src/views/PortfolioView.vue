<script setup lang="ts">
import { Lightbulb, LoaderCircle, RefreshCw, Telescope, Waypoints } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import ExplainBars from '../components/ExplainBars.vue'
import ForecastFan from '../components/ForecastFan.vue'
import PageHeader from '../components/PageHeader.vue'
import RiskMeter from '../components/RiskMeter.vue'
import RulesSwitch from '../components/RulesSwitch.vue'
import TermHint from '../components/TermHint.vue'
import AdviceList from '../components/portfolio/AdviceList.vue'
import NowCard from '../components/portfolio/NowCard.vue'
import RecordsCard from '../components/portfolio/RecordsCard.vue'
import StudyCard from '../components/portfolio/StudyCard.vue'
import { useMeta } from '../composables/useMeta'
import { usePortfolio } from '../composables/usePortfolio'
import type { AppLocale } from '../types'
import { num, pct } from '../utils/format'

// «Мой портфель»: слева ввод как в АСУ, справа – IGPA сейчас, прогноз IGPA-Hybrid на следующий год с коридором 10–90%
// и риском снижения, объяснение SHAP облегчённого CatBoost и три совета
const { t, locale } = useI18n()
const lang = computed(() => locale.value as AppLocale)
const { meta } = useMeta()
const { state, result, loading, error, add, retry } = usePortfolio()
const year = computed(() => meta.value?.current_year ?? 2025)
const labels = computed<[string, string]>(() => [`${year.value}/${(year.value + 1) % 100}`, `${year.value + 1}/${(year.value + 2) % 100}`])

function raiseGpa(step: number) {
  state.gpa = Math.min(4, +(state.gpa + step).toFixed(2))
}
</script>

<template>
  <div>
    <PageHeader :eyebrow="t('nav.portfolio')" :title="t('portfolio.title')" :lead="t('portfolio.lead')">
      <RulesSwitch v-model="state.rules" />
    </PageHeader>

    <section class="mx-auto grid max-w-7xl items-start gap-6 px-4 sm:px-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
      <div class="space-y-6">
        <StudyCard class="animate-rise" />
        <RecordsCard class="animate-rise [animation-delay:80ms]" />
      </div>

      <div class="relative space-y-6">
        <div v-if="loading" class="absolute -top-8 right-0 flex items-center gap-1.5 text-xs text-faint" role="status">
          <LoaderCircle class="h-3.5 w-3.5 animate-spin" />{{ t('portfolio.computing') }}
        </div>
        <div v-if="error && !result" class="card flex items-center gap-3 p-6 text-sm text-bad">
          {{ t('common.loadFailed') }}
          <button class="btn-ghost ml-auto !py-1" @click="retry"><RefreshCw class="h-4 w-4" />{{ t('common.retry') }}</button>
        </div>
        <template v-if="result">
          <div class="space-y-6 transition-opacity duration-300" :class="loading && 'opacity-60'">
            <NowCard :now="result.now" class="animate-rise" />

            <div class="card animate-rise p-6 [animation-delay:80ms]">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <h2 class="flex items-center gap-2 font-bold"><Telescope class="h-5 w-5 text-primary" />{{ t('forecast.title') }}</h2>
                <span class="chip">IGPA-Hybrid <TermHint term="hybrid" /></span>
              </div>
              <div class="mt-4 grid grid-cols-2 gap-4">
                <div>
                  <p class="text-xs text-faint">{{ t('forecast.mean') }}</p>
                  <p class="text-4xl font-bold tracking-tight">{{ num(result.forecast.mean, lang) }}</p>
                </div>
                <div>
                  <p class="flex items-center gap-1 text-xs text-faint">{{ t('forecast.band') }} <TermHint term="band" /></p>
                  <p class="num mt-1.5 text-xl font-semibold">{{ num(result.forecast.p10, lang) }} – {{ num(result.forecast.p90, lang) }}</p>
                </div>
              </div>
              <ForecastFan
                class="mt-2"
                :now="result.now.igpa"
                :mean="result.forecast.mean"
                :p10="result.forecast.p10"
                :p90="result.forecast.p90"
                :labels="labels"
              />
              <RiskMeter class="mt-2" :risk="result.forecast.risk" />
              <p class="mt-4 rounded-2xl bg-surface-2 px-4 py-3 text-xs leading-relaxed text-muted">
                {{ t('forecast.second', { pred: num(result.catboost.pred, lang), lo: num(result.catboost.p10, lang), hi: num(result.catboost.p90, lang), risk: pct(result.catboost.risk, lang) }) }}
                <template v-if="!state.hasPrev"> {{ t('forecast.noPrev') }}</template>
              </p>
            </div>

            <div class="card animate-rise p-6 [animation-delay:160ms]">
              <h2 class="flex items-center gap-2 font-bold"><Waypoints class="h-5 w-5 text-primary" />{{ t('explain.title') }} <TermHint term="shap" /></h2>
              <p class="mt-1 text-sm text-muted">{{ t('explain.lead') }}</p>
              <ExplainBars class="mt-5" :factors="result.explanation" />
            </div>

            <div class="card animate-rise p-6 [animation-delay:240ms]">
              <h2 class="flex items-center gap-2 font-bold"><Lightbulb class="h-5 w-5 text-accent" />{{ t('advice.title') }}</h2>
              <p class="mt-1 text-sm text-muted">{{ t('advice.lead') }}</p>
              <AdviceList class="mt-5" :advice="result.advice" @add-record="add" @raise-gpa="raiseGpa" />
            </div>
          </div>
        </template>
        <template v-else-if="!error">
          <div v-for="i in 3" :key="i" class="skeleton h-64" />
        </template>
      </div>
    </section>
  </div>
</template>
