<script setup lang="ts">
import { BriefcaseBusiness, Calculator, FlaskConical, House, Info, Moon, Sun, Users } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { useLocale } from '../composables/useLocale'
import { useTheme } from '../composables/useTheme'
import LogoMark from './LogoMark.vue'

// шапка: полупрозрачная с размытием; на телефоне разделы – в нижней панели
const { t } = useI18n()
const route = useRoute()
const { theme, toggleTheme } = useTheme()
const { locale, locales } = useLocale()

// short – подпись в нижней панели телефона, где на раздел меньше 70 px
const items = computed(() =>
  (
    [
      ['/', 'home', House],
      ['/portfolio', 'portfolio', BriefcaseBusiness],
      ['/stand', 'stand', Users],
      ['/quick', 'quick', Calculator],
      ['/research', 'research', FlaskConical],
      ['/about', 'about', Info],
    ] as const
  ).map(([to, key, icon]) => ({ to, icon, label: t(`nav.${key}`), short: t(`nav.${key}Short`) })),
)
// «Стенд» подсвечен и на карточке студента
const active = (to: string) => (to === '/' ? route.path === '/' : route.path.startsWith(to))
</script>

<template>
  <header class="fixed inset-x-0 top-0 z-50 border-b border-line bg-bg/85 text-ink backdrop-blur-xl">
    <div class="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4 sm:px-6">
      <RouterLink to="/" class="flex items-center gap-2.5">
        <LogoMark class="h-8 w-8" />
        <span class="text-lg font-bold tracking-tight">Igpa<span class="text-primary">Lab</span></span>
      </RouterLink>
      <nav class="ml-4 hidden items-center gap-1 lg:flex">
        <RouterLink
          v-for="item in items"
          :key="item.to"
          :to="item.to"
          class="rounded-full px-3.5 py-1.5 text-sm font-medium text-muted transition-colors hover:bg-surface-2 hover:text-ink"
          :class="active(item.to) && '!bg-primary-soft !text-primary-strong'"
        >
          {{ item.label }}
        </RouterLink>
      </nav>
      <div class="ml-auto flex items-center gap-2">
        <div class="flex rounded-full bg-surface-2 p-0.5" role="group" :aria-label="t('nav.language')">
          <button
            v-for="l in locales"
            :key="l.code"
            class="rounded-full px-2.5 py-1 text-xs font-semibold transition-colors"
            :class="locale === l.code ? 'bg-surface text-ink shadow-sm' : 'opacity-70 hover:opacity-100'"
            :aria-pressed="locale === l.code"
            @click="locale = l.code"
          >
            {{ l.label }}
          </button>
        </div>
        <button
          class="flex h-9 w-9 items-center justify-center rounded-full bg-surface-2 transition-colors hover:bg-line"
          :aria-label="t('nav.theme')"
          @click="toggleTheme"
        >
          <Sun v-if="theme === 'dark'" class="h-4.5 w-4.5" />
          <Moon v-else class="h-4.5 w-4.5" />
        </button>
      </div>
    </div>
  </header>

  <!-- нижняя навигация на телефоне и планшете -->
  <nav class="fixed inset-x-0 bottom-0 z-50 border-t border-line bg-bg/90 backdrop-blur-xl lg:hidden">
    <div class="grid grid-cols-6">
      <RouterLink
        v-for="item in items"
        :key="item.to"
        :to="item.to"
        class="flex flex-col items-center gap-1 py-2.5 text-[10px] font-medium tracking-tight text-faint"
        :class="active(item.to) && '!text-primary-strong'"
      >
        <component :is="item.icon" class="h-5 w-5" aria-hidden="true" />
        <span class="max-w-full truncate px-1">{{ item.short }}</span>
      </RouterLink>
    </div>
  </nav>
</template>
