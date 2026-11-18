<script setup lang="ts">
import { BookMarked, Boxes, BrainCircuit, Calculator, Database, GraduationCap, LayoutPanelTop, Microscope, Server, UserRound } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import PageHeader from '../components/PageHeader.vue'
import { LINKS } from '../links'
import type { AppLocale } from '../types'
import { int } from '../utils/format'

// «О проекте»: зачем стенд, из чего состоит, на чём сделан, кто автор и на что ссылается
const { t, locale } = useI18n()
const lang = computed(() => locale.value as AppLocale)

// автотесты по модулям (pytest и Vitest); обновлять при изменении числа тестов
const TESTS = { igpa: 75, data: 26, research: 6, model: 49, backend: 16, frontend: 20 } as const
const total = Object.values(TESTS).reduce((a, b) => a + b, 0)

const facts = computed(() => [
  { key: 'students', value: int(6000, lang.value) },
  { key: 'catalog', value: '16 · 9' },
  { key: 'models', value: '8' },
  { key: 'tests', value: int(total, lang.value) },
])
const modules = [
  { key: 'igpa', icon: Calculator },
  { key: 'data', icon: Database },
  { key: 'research', icon: Microscope },
  { key: 'model', icon: BrainCircuit },
  { key: 'backend', icon: Server },
  { key: 'frontend', icon: LayoutPanelTop },
] as const
const STACK = ['Python 3.12', 'pandas', 'scikit-learn', 'CatBoost', 'SHAP', 'FastAPI', 'pytest', 'Vue 3', 'TypeScript', 'Tailwind CSS 4', 'vue-i18n', 'ECharts', 'Vitest', 'Docker', 'Make']
const sources = computed(() => [
  { key: 'aitu', href: LINKS.aitu },
  { key: 'uci', href: LINKS.uci },
  { key: 'regulation', href: '' },
])
</script>

<template>
  <div>
    <PageHeader :eyebrow="t('nav.about')" :title="t('about.title')" :lead="t('about.lead')" />

    <section class="mx-auto max-w-7xl space-y-6 px-4 sm:px-6">
      <dl class="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <div v-for="(f, i) in facts" :key="f.key" v-reveal="i" class="card relative overflow-hidden p-5">
          <span class="absolute inset-y-5 left-0 w-1 rounded-r-full bg-accent" aria-hidden="true" />
          <dd class="num text-3xl font-bold tracking-tight">{{ f.value }}</dd>
          <dt class="mt-1 text-sm text-muted">{{ t(`about.facts.${f.key}`) }}</dt>
        </div>
      </dl>

      <div class="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <div v-reveal class="card p-6">
          <h2 class="flex items-center gap-2 font-bold"><BookMarked class="h-5 w-5 text-primary" />{{ t('about.whyTitle') }}</h2>
          <p class="mt-3 text-sm leading-relaxed text-muted">{{ t('about.why1') }}</p>
          <p class="mt-3 text-sm leading-relaxed text-muted">{{ t('about.why2') }}</p>
          <p class="mt-3 text-sm leading-relaxed text-muted">{{ t('about.why3') }}</p>
        </div>
        <div v-reveal class="card p-6">
          <h2 class="flex items-center gap-2 font-bold"><GraduationCap class="h-5 w-5 text-primary" />{{ t('about.thesisTitle') }}</h2>
          <p class="mt-3 text-sm leading-relaxed font-medium">{{ t('about.thesis') }}</p>
          <div class="mt-5 space-y-3">
            <div class="flex items-start gap-3 rounded-2xl bg-surface-2 p-4">
              <UserRound class="mt-0.5 h-5 w-5 shrink-0 text-primary" />
              <div>
                <p class="text-xs text-faint">{{ t('about.authorRole') }}</p>
                <p class="font-semibold">{{ t('about.author') }}</p>
                <p class="text-sm text-muted">{{ t('about.program') }}</p>
              </div>
            </div>
            <div class="flex items-start gap-3 rounded-2xl bg-surface-2 p-4">
              <GraduationCap class="mt-0.5 h-5 w-5 shrink-0 text-accent" />
              <div>
                <p class="text-xs text-faint">{{ t('about.supervisorRole') }}</p>
                <p class="font-semibold">{{ t('about.supervisor') }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-reveal class="card p-6">
        <h2 class="flex items-center gap-2 font-bold"><Boxes class="h-5 w-5 text-primary" />{{ t('about.modulesTitle') }}</h2>
        <ul class="mt-5 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <li v-for="(m, i) in modules" :key="m.key" v-reveal="i" class="relative rounded-2xl border border-line p-4 pl-5">
            <span class="absolute inset-y-4 left-0 w-1 rounded-r-full bg-primary/60" aria-hidden="true" />
            <p class="flex items-center gap-2 font-semibold"><component :is="m.icon" class="h-4.5 w-4.5 text-primary" />{{ t(`about.module.${m.key}Title`) }}</p>
            <p class="mt-1.5 text-sm leading-relaxed text-muted">{{ t(`about.module.${m.key}`) }}</p>
            <p class="num mt-2 text-xs text-faint">{{ t('about.testsCount', { n: TESTS[m.key] }) }}</p>
          </li>
        </ul>
      </div>

      <div class="grid gap-6 lg:grid-cols-2">
        <div v-reveal class="card p-6">
          <h2 class="font-bold">{{ t('about.stackTitle') }}</h2>
          <div class="mt-4 flex flex-wrap gap-2">
            <span v-for="s in STACK" :key="s" class="chip">{{ s }}</span>
          </div>
          <p class="mt-4 text-sm leading-relaxed text-muted">{{ t('about.stackNote') }}</p>
        </div>
        <div v-reveal class="card p-6">
          <h2 class="font-bold">{{ t('about.sourcesTitle') }}</h2>
          <ul class="mt-4 space-y-3 text-sm leading-relaxed">
            <li v-for="s in sources" :key="s.key" class="text-muted">
              <a v-if="s.href" :href="s.href" target="_blank" rel="noopener" class="hover:text-primary-strong">{{ t(`about.source.${s.key}`) }} ↗</a>
              <span v-else>{{ t(`about.source.${s.key}`) }}</span>
            </li>
          </ul>
        </div>
      </div>
    </section>
  </div>
</template>
