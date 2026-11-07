<script setup lang="ts">
import {
  ArrowRight,
  BrainCircuit,
  BriefcaseBusiness,
  Calculator,
  Database,
  FileSpreadsheet,
  FlaskConical,
  Globe,
  ScanSearch,
  Sigma,
  Users,
} from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import LiveFormula from '../components/home/LiveFormula.vue'

const { t } = useI18n()

const modes = computed(() => [
  { to: '/portfolio', icon: BriefcaseBusiness, key: 'portfolio' },
  { to: '/stand', icon: Users, key: 'stand' },
  { to: '/quick', icon: Calculator, key: 'quick' },
])
// главное из исследования (docs/research.md): последняя проверка 2024/25 → 2025/26 и доработки после шага 8
const findings = computed(() => (['gain', 'share', 'auc', 'robust'] as const).map((key) => ({ key })))
const pipeline = computed(() => [
  { icon: FileSpreadsheet, key: 'templates' },
  { icon: Database, key: 'synthetic' },
  { icon: Sigma, key: 'calculator' },
  { icon: BrainCircuit, key: 'models' },
  { icon: Globe, key: 'site' },
])
</script>

<template>
  <div>
    <!-- первый экран: заголовок и живая формула -->
    <section class="relative overflow-hidden">
      <div class="hero-glow pointer-events-none absolute inset-0" aria-hidden="true" />
      <div class="hero-grid pointer-events-none absolute inset-0" aria-hidden="true" />
      <div class="relative mx-auto grid max-w-7xl items-center gap-10 px-4 pt-28 pb-16 sm:px-6 lg:grid-cols-[1.05fr_1fr] lg:gap-14 lg:pt-32">
        <div class="animate-rise">
          <span class="chip"><FlaskConical class="h-4 w-4 text-accent" />{{ t('home.badge') }}</span>
          <h1 class="mt-5 text-4xl leading-[1.08] font-bold tracking-tight sm:text-5xl xl:text-[3.5rem]">
            {{ t('home.title') }}
            <span class="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">{{ t('home.titleAccent') }}</span>
          </h1>
          <p class="mt-5 max-w-xl text-lg leading-relaxed text-muted">{{ t('home.lead') }}</p>
          <div class="mt-8 flex flex-wrap gap-3">
            <RouterLink v-ripple to="/portfolio" class="btn-primary">
              {{ t('home.ctaPortfolio') }}<ArrowRight class="h-4 w-4" />
            </RouterLink>
            <RouterLink v-ripple to="/stand" class="btn-ghost">{{ t('home.ctaStand') }}</RouterLink>
          </div>
          <dl class="mt-10 grid max-w-xl grid-cols-3 gap-4 border-t border-line pt-6">
            <div v-for="k in ['students', 'types', 'rules'] as const" :key="k">
              <dt class="text-xs text-faint">{{ t(`home.facts.${k}Label`) }}</dt>
              <dd class="num mt-1 text-2xl font-bold">{{ t(`home.facts.${k}`) }}</dd>
            </div>
          </dl>
        </div>
        <LiveFormula class="animate-rise [animation-delay:120ms]" />
      </div>
    </section>

    <!-- три режима стенда -->
    <section class="mx-auto max-w-7xl px-4 py-12 sm:px-6">
      <p v-reveal class="eyebrow">{{ t('home.modesEyebrow') }}</p>
      <h2 v-reveal class="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">{{ t('home.modesTitle') }}</h2>
      <div class="mt-8 grid gap-5 md:grid-cols-3">
        <RouterLink
          v-for="(m, i) in modes"
          :key="m.key"
          v-reveal="i"
          :to="m.to"
          class="card lift group flex flex-col p-6"
        >
          <span class="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary-soft text-primary-strong">
            <component :is="m.icon" class="h-5 w-5" />
          </span>
          <h3 class="mt-5 text-lg font-bold">{{ t(`modes.${m.key}.title`) }}</h3>
          <p class="mt-2 flex-1 text-sm leading-relaxed text-muted">{{ t(`modes.${m.key}.text`) }}</p>
          <span class="mt-5 inline-flex items-center gap-1.5 text-sm font-semibold text-primary-strong">
            {{ t('home.open') }}<ArrowRight class="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </span>
        </RouterLink>
      </div>
    </section>

    <!-- главное из исследования -->
    <section class="mx-auto max-w-7xl px-4 py-12 sm:px-6">
      <div class="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p v-reveal class="eyebrow">{{ t('home.findingsEyebrow') }}</p>
          <h2 v-reveal class="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">{{ t('home.findingsTitle') }}</h2>
        </div>
        <RouterLink to="/research" class="btn-ghost"><ScanSearch class="h-4 w-4" />{{ t('home.toResearch') }}</RouterLink>
      </div>
      <div class="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div v-for="(f, i) in findings" :key="f.key" v-reveal="i" class="card relative overflow-hidden p-6">
          <span class="absolute inset-y-6 left-0 w-1 rounded-r-full bg-accent" aria-hidden="true" />
          <p class="num text-3xl font-bold tracking-tight">{{ t(`findings.${f.key}.value`) }}</p>
          <p class="mt-2 text-sm font-semibold">{{ t(`findings.${f.key}.title`) }}</p>
          <p class="mt-2 text-sm leading-relaxed text-muted">{{ t(`findings.${f.key}.text`) }}</p>
        </div>
      </div>
    </section>

    <!-- как устроен стенд -->
    <section class="mx-auto max-w-7xl px-4 py-12 sm:px-6">
      <p v-reveal class="eyebrow">{{ t('home.pipelineEyebrow') }}</p>
      <h2 v-reveal class="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">{{ t('home.pipelineTitle') }}</h2>
      <ol class="mt-8 grid gap-4 md:grid-cols-5">
        <li v-for="(p, i) in pipeline" :key="p.key" v-reveal="i" class="relative">
          <div class="card h-full p-5">
            <span class="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent">
              <component :is="p.icon" class="h-5 w-5" />
            </span>
            <h3 class="mt-4 font-bold">{{ t(`pipeline.${p.key}.title`) }}</h3>
            <p class="mt-1.5 text-sm leading-relaxed text-muted">{{ t(`pipeline.${p.key}.text`) }}</p>
          </div>
          <ArrowRight
            v-if="i < pipeline.length - 1"
            class="absolute top-1/2 -right-3.5 z-10 hidden h-5 w-5 -translate-y-1/2 text-faint md:block"
            aria-hidden="true"
          />
        </li>
      </ol>
    </section>

    <!-- честное предупреждение о данных -->
    <section class="mx-auto max-w-7xl px-4 pt-6 sm:px-6">
      <div v-reveal class="card flex flex-col gap-4 border-accent/30 bg-accent-soft/40 p-6 sm:flex-row sm:items-start">
        <Database class="h-6 w-6 shrink-0 text-accent" />
        <div>
          <h2 class="font-bold">{{ t('home.syntheticTitle') }}</h2>
          <p class="mt-1.5 text-sm leading-relaxed text-muted">{{ t('home.syntheticText') }}</p>
        </div>
      </div>
    </section>
  </div>
</template>
