<script setup lang="ts">
import { computed } from 'vue'

// горизонтальные полосы с подписью и значением текстом; полосы вырастают от нуля по очереди
export interface Bar {
  key: string
  label: string
  value: number
  text: string
  cls?: string
  note?: string
}
const props = defineProps<{ bars: Bar[]; max?: number }>()
const top = computed(() => props.max ?? Math.max(...props.bars.map((b) => Math.abs(b.value)), 1e-9))
</script>

<template>
  <ul class="space-y-3">
    <li v-for="(b, i) in bars" :key="b.key" class="grid grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)_4.5rem] items-center gap-3 text-sm">
      <span class="min-w-0">
        <span class="block truncate" :title="b.label">{{ b.label }}</span>
        <span v-if="b.note" class="block truncate text-xs text-faint">{{ b.note }}</span>
      </span>
      <div class="h-2.5 overflow-hidden rounded-full bg-surface-2">
        <div class="grow-x h-full origin-left rounded-full" :class="b.cls ?? 'bg-primary'" :style="{ width: `${(Math.max(0, b.value) / top) * 100}%`, animationDelay: `${i * 60}ms` }" />
      </div>
      <span class="num text-right font-semibold">{{ b.text }}</span>
    </li>
  </ul>
</template>
