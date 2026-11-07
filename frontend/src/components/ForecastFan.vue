<script setup lang="ts">
import { LineChart } from 'echarts/charts'
import { GridComponent, MarkLineComponent, TooltipComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { SVGRenderer } from 'echarts/renderers'
import { computed } from 'vue'
import VChart from 'vue-echarts'
import 'vue-echarts/style.css'
import { useI18n } from 'vue-i18n'
import { useTheme } from '../composables/useTheme'
import type { AppLocale } from '../types'
import { axisStyle, css, reducedMotion, tooltipStyle } from '../utils/chart'
import { num } from '../utils/format'

use([LineChart, GridComponent, MarkLineComponent, TooltipComponent, SVGRenderer])

// «веер» прогноза: из сегодняшнего IGPA расходится коридор 10–90% до следующего года, линия – средний прогноз;
// fact – что случилось на самом деле (для студентов стенда)
const props = defineProps<{ now: number; mean: number; p10: number; p90: number; fact?: number | null; labels: [string, string] }>()
const { t, locale } = useI18n()
const { theme } = useTheme()
const lang = computed(() => locale.value as AppLocale)

const option = computed(() => {
  void theme.value // перерисовать при смене темы: цвета читаются из CSS-переменных
  const primary = css('--primary')
  const lo = Math.min(props.now, props.p10, props.fact ?? Infinity)
  const hi = Math.max(props.now, props.p90, props.fact ?? -Infinity)
  const pad = Math.max(0.08, (hi - lo) * 0.25)
  const series: Record<string, unknown>[] = [
    { name: 'p10', type: 'line', data: [props.now, props.p10], stack: 'band', symbol: 'none', lineStyle: { opacity: 0 }, silent: true },
    {
      name: 'band',
      type: 'line',
      data: [0, props.p90 - props.p10],
      stack: 'band',
      symbol: 'none',
      lineStyle: { opacity: 0 },
      areaStyle: { color: primary, opacity: 0.18 },
      silent: true,
    },
    {
      name: 'mean',
      type: 'line',
      data: [props.now, props.mean],
      symbol: 'circle',
      symbolSize: 10,
      lineStyle: { color: primary, width: 2.5 },
      itemStyle: { color: primary, borderColor: css('--surface'), borderWidth: 2 },
      label: { show: true, position: 'top', color: css('--ink'), fontWeight: 600, formatter: (p: { value: number }) => num(p.value, lang.value) },
    },
  ]
  if (props.fact != null) {
    series.push({
      name: 'fact',
      type: 'line',
      data: [null, props.fact],
      symbol: 'diamond',
      symbolSize: 13,
      itemStyle: { color: css('--accent'), borderColor: css('--surface'), borderWidth: 2 },
      label: { show: true, position: 'right', color: css('--accent'), fontWeight: 700, formatter: (p: { value: number }) => num(p.value, lang.value) },
    })
  }
  return {
    animation: !reducedMotion(),
    animationDuration: 900,
    grid: { left: 44, right: 56, top: 28, bottom: 28 },
    xAxis: { type: 'category', data: props.labels, boundaryGap: false, ...axisStyle(), splitLine: { show: false } },
    yAxis: {
      type: 'value',
      min: Math.max(0, +(lo - pad).toFixed(2)),
      max: Math.min(4, +(hi + pad).toFixed(2)),
      ...axisStyle(),
      axisLabel: { ...axisStyle().axisLabel, formatter: (v: number) => num(v, lang.value) },
    },
    tooltip: {
      trigger: 'axis',
      ...tooltipStyle(),
      formatter: () =>
        `${t('forecast.mean')}: <b>${num(props.mean, lang.value)}</b><br>${t('forecast.band')}: ${num(props.p10, lang.value)}–${num(props.p90, lang.value)}` +
        (props.fact != null ? `<br>${t('forecast.fact')}: <b>${num(props.fact, lang.value)}</b>` : ''),
    },
    series,
  }
})
</script>

<template>
  <div class="h-56 w-full" role="img" :aria-label="t('forecast.aria', { now: num(now, lang), mean: num(mean, lang), lo: num(p10, lang), hi: num(p90, lang) })">
    <VChart :option="option" autoresize />
  </div>
</template>
