<script setup lang="ts">
import { BookText, BrainCircuit, Database, RefreshCw, Scale, ShieldCheck } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '../components/PageHeader.vue'
import DataSection from '../components/research/DataSection.vue'
import MethodSection from '../components/research/MethodSection.vue'
import ModelsSection from '../components/research/ModelsSection.vue'
import NormSection from '../components/research/NormSection.vue'
import ReliabilitySection from '../components/research/ReliabilitySection.vue'
import { useResearch } from '../composables/useResearch'

// «Исследование»: пять вкладок, выбранная – в адресе (?tab=), чтобы ей можно было поделиться
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { research, failed, retry } = useResearch()
const TABS = [
  { key: 'models', icon: BrainCircuit },
  { key: 'norm', icon: Scale },
  { key: 'reliability', icon: ShieldCheck },
  { key: 'data', icon: Database },
  { key: 'method', icon: BookText },
] as const
const tab = computed({
  get: () => (TABS.some((x) => x.key === route.query.tab) ? String(route.query.tab) : 'models'),
  set: (v: string) => router.replace({ query: { ...route.query, tab: v } }),
})
</script>

<template>
  <div>
    <PageHeader :eyebrow="t('nav.research')" :title="t('research.title')" :lead="t('research.lead')" />
    <section class="mx-auto max-w-7xl px-4 sm:px-6">
      <div class="sticky top-16 z-30 -mx-4 bg-bg/90 px-4 py-3 backdrop-blur-xl sm:mx-0 sm:px-0">
        <div class="flex gap-1 overflow-x-auto rounded-full bg-surface-2 p-1" role="tablist">
          <button
            v-for="x in TABS"
            :key="x.key"
            role="tab"
            :aria-selected="tab === x.key"
            class="flex shrink-0 items-center gap-1.5 rounded-full px-4 py-2 text-sm font-semibold transition-colors"
            :class="tab === x.key ? 'bg-surface text-primary-strong shadow-sm' : 'text-muted hover:text-ink'"
            @click="tab = x.key"
          >
            <component :is="x.icon" class="h-4 w-4" />{{ t(`research.tab.${x.key}`) }}
          </button>
        </div>
      </div>

      <div v-if="failed" class="card mt-4 flex items-center gap-3 p-6 text-sm text-bad">
        {{ t('common.loadFailed') }}
        <button class="btn-ghost ml-auto !py-1" @click="retry"><RefreshCw class="h-4 w-4" />{{ t('common.retry') }}</button>
      </div>
      <div v-else-if="research" class="mt-4">
        <Transition name="page" mode="out-in">
          <ModelsSection v-if="tab === 'models'" :data="research" />
          <NormSection v-else-if="tab === 'norm'" :data="research" />
          <ReliabilitySection v-else-if="tab === 'reliability'" :data="research" />
          <DataSection v-else-if="tab === 'data'" :data="research" />
          <MethodSection v-else />
        </Transition>
      </div>
      <div v-else class="mt-4 space-y-4">
        <div class="skeleton h-64" />
        <div class="skeleton h-48" />
      </div>
    </section>
  </div>
</template>
