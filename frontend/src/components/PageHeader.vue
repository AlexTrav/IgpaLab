<script setup lang="ts">
// заголовок страницы: надзаголовок, заголовок и вводный абзац; справа – слот для переключателей
defineProps<{ eyebrow: string; title: string; lead?: string }>()
</script>

<template>
  <header class="mx-auto max-w-7xl px-4 pt-28 pb-8 sm:px-6">
    <div class="flex flex-wrap items-end justify-between gap-6">
      <div class="max-w-3xl animate-rise">
        <p class="eyebrow">{{ eyebrow }}</p>
        <h1 class="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">{{ title }}</h1>
        <p v-if="lead" class="mt-3 text-base leading-relaxed text-muted">{{ lead }}</p>
      </div>
      <slot />
    </div>
  </header>
</template>
