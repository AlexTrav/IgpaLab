<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { LINKS } from '../links'
import LogoMark from './LogoMark.vue'

const { t } = useI18n()
const sections = computed(() =>
  (['home', 'portfolio', 'stand', 'quick', 'research', 'about'] as const).map((key) => ({
    to: key === 'home' ? '/' : `/${key}`,
    label: t(`nav.${key}`),
  })),
)
const links = computed(() => [
  { href: LINKS.api, label: t('footer.api') },
  { href: LINKS.aitu, label: t('footer.aitu') },
  { href: LINKS.uci, label: 'UCI Student Performance' },
])
</script>

<template>
  <footer class="mt-24 border-t border-line bg-surface-2/50 pb-20 lg:pb-0">
    <div class="mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:px-6 md:grid-cols-[1.6fr_1fr_1fr]">
      <div>
        <div class="flex items-center gap-2.5">
          <LogoMark class="h-9 w-9" />
          <span class="text-lg font-bold text-ink">Igpa<span class="text-primary">Lab</span></span>
        </div>
        <p class="mt-4 max-w-md text-sm leading-relaxed text-muted">{{ t('footer.tagline') }}</p>
        <p class="mt-3 max-w-md text-xs leading-relaxed text-faint">{{ t('footer.project') }}</p>
      </div>
      <div>
        <h3 class="eyebrow">{{ t('footer.sections') }}</h3>
        <ul class="mt-4 space-y-2 text-sm">
          <li v-for="s in sections" :key="s.to">
            <RouterLink :to="s.to" class="text-muted transition-colors hover:text-primary-strong">{{ s.label }}</RouterLink>
          </li>
        </ul>
      </div>
      <div>
        <h3 class="eyebrow">{{ t('footer.links') }}</h3>
        <ul class="mt-4 space-y-2 text-sm">
          <li v-for="l in links" :key="l.href">
            <a :href="l.href" target="_blank" rel="noopener" class="text-muted transition-colors hover:text-primary-strong">{{ l.label }} ↗</a>
          </li>
        </ul>
      </div>
    </div>
    <div class="border-t border-line">
      <div class="mx-auto max-w-7xl px-4 py-5 text-xs leading-relaxed text-faint sm:px-6">
        <p>{{ t('footer.disclaimer') }}</p>
      </div>
    </div>
  </footer>
</template>
