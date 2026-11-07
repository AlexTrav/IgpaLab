<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { SCALE } from '../utils/igpa'

// полоса шкалы IGPA 0–4: вклады GPA, iROS и SSCI «наливаются» слева направо, ширина каждой части плавно
// перетекает при пересчёте (класс .pour). Между частями – зазор цвета фона, подписи частей – рядом (не только цвет)
const props = withDefaults(defineProps<{ gpa: number; iros: number; ssci: number; ticks?: boolean; thin?: boolean }>(), {
  ticks: true,
  thin: false,
})
const { t } = useI18n()
const width = (x: number) => `${Math.max(0, Math.min(1, x / SCALE)) * 100}%`
const parts = computed(() => [
  { key: 'gpa', value: props.gpa, cls: 'bg-gpa' },
  { key: 'iros', value: props.iros, cls: 'bg-iros' },
  { key: 'ssci', value: props.ssci, cls: 'bg-ssci' },
])
</script>

<template>
  <div>
    <div
      class="flex w-full gap-[2px] overflow-hidden rounded-full bg-surface-2"
      :class="thin ? 'h-2.5' : 'h-5'"
      role="img"
      :aria-label="t('formula.barLabel', { gpa: gpa.toFixed(2), iros: iros.toFixed(2), ssci: ssci.toFixed(2) })"
    >
      <div
        v-for="p in parts"
        :key="p.key"
        class="pour h-full shrink-0 first:rounded-l-full last:rounded-r-full"
        :class="p.cls"
        :style="{ width: width(p.value) }"
      />
    </div>
    <div v-if="ticks" class="num mt-1.5 flex justify-between text-[11px] text-faint" aria-hidden="true">
      <span v-for="i in SCALE + 1" :key="i">{{ i - 1 }}</span>
    </div>
  </div>
</template>
