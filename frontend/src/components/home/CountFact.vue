<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCountUp } from '../../composables/useCountUp'
import type { AppLocale } from '../../types'
import { int } from '../../utils/format'

// число первого экрана «докручивается» от нуля при открытии страницы
const props = defineProps<{ value: number; label: string }>()
const { locale } = useI18n()
const target = ref(0)
const shown = useCountUp(target, 1400)
onMounted(() => setTimeout(() => (target.value = props.value), 250))
const text = computed(() => int(shown.value ?? 0, locale.value as AppLocale))
</script>

<template>
  <div>
    <dt class="text-xs text-faint">{{ label }}</dt>
    <dd class="num mt-1 text-2xl font-bold" :aria-label="int(value, locale as AppLocale)">{{ text }}</dd>
  </div>
</template>
