<script setup lang="ts">
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { SVGRenderer } from 'echarts/renderers'
import { computed } from 'vue'
import VChart from 'vue-echarts'
import 'vue-echarts/style.css'
import { useI18n } from 'vue-i18n'
import { useTheme } from '../../composables/useTheme'
import type { AppLocale, HistoryYear, Student } from '../../types'
import { axisStyle, css, reducedMotion, tooltipStyle } from '../../utils/chart'
import { num } from '../../utils/format'

use([LineChart, GridComponent, LegendComponent, TooltipComponent, SVGRenderer])

// история IGPA по учебным годам: по данным АСУ (сплошная) и «на самом деле» (пунктир, достижения, не внесённые в АСУ);
// в конце – прогноз на следующий год с коридором 10–90%, который расходится веером от последнего года
const props = defineProps<{ history: HistoryYear[]; forecast: Student['forecast'] }>()
const { t, locale } = useI18n()
const { theme } = useTheme()
const lang = computed(() => locale.value as AppLocale)
const label = (y: number) => `${y}/${(y + 1) % 100}`

const option = computed(() => {
  void theme.value
  const done = props.history.filter((h) => h.obs_igpa != null)
  const years = done.map((h) => h.year)
  const fc = props.forecast
  const next = years.length ? years[years.length - 1] + 1 : null
  const x = [...years, ...(fc && next ? [next] : [])].map(label)
  const pad = (arr: (number | null)[]) => [...arr, ...(fc && next ? [null] : [])]
  const last = done.length - 1
  const fanBase = x.map((_, i) => (fc && i === last ? fc.igpa_now : fc && i === last + 1 ? fc.p10 : null))
  const fanWidth = x.map((_, i) => (fc && i === last ? 0 : fc && i === last + 1 ? fc.p90 - fc.p10 : null))
  const fcLine = x.map((_, i) => (fc && i === last ? fc.igpa_now : fc && i === last + 1 ? fc.pred : null))
  const primary = css('--primary')
  return {
    animation: !reducedMotion(),
    animationDuration: 900,
    grid: { left: 44, right: 20, top: 36, bottom: 30 },
    legend: { top: 0, left: 0, itemWidth: 16, itemHeight: 8, textStyle: { color: css('--muted'), fontSize: 12 }, data: [t('student.igpaAsu'), t('student.igpaTrue'), t('student.forecast')] },
    xAxis: { type: 'category', data: x, boundaryGap: false, ...axisStyle(), splitLine: { show: false } },
    yAxis: { type: 'value', scale: true, ...axisStyle(), axisLabel: { ...axisStyle().axisLabel, formatter: (v: number) => num(v, lang.value, 1) } },
    tooltip: {
      trigger: 'axis',
      ...tooltipStyle(),
      valueFormatter: (v: number | null) => (v == null ? '–' : num(v, lang.value)),
    },
    series: [
      { name: 'fanBase', type: 'line', data: fanBase, stack: 'fan', symbol: 'none', lineStyle: { opacity: 0 }, tooltip: { show: false }, silent: true },
      { name: 'fanWidth', type: 'line', data: fanWidth, stack: 'fan', symbol: 'none', lineStyle: { opacity: 0 }, areaStyle: { color: primary, opacity: 0.16 }, tooltip: { show: false }, silent: true },
      { name: t('student.igpaTrue'), type: 'line', data: pad(done.map((h) => h.true_igpa)), symbol: 'circle', symbolSize: 6, lineStyle: { type: 'dashed', width: 1.5, color: css('--faint') }, itemStyle: { color: css('--faint') } },
      { name: t('student.igpaAsu'), type: 'line', data: pad(done.map((h) => h.obs_igpa)), symbol: 'circle', symbolSize: 9, lineStyle: { width: 2.5, color: primary }, itemStyle: { color: primary, borderColor: css('--surface'), borderWidth: 2 } },
      ...(fc
        ? [{ name: t('student.forecast'), type: 'line', data: fcLine, symbol: 'circle', symbolSize: 9, lineStyle: { width: 2.5, type: 'dotted', color: css('--accent') }, itemStyle: { color: css('--accent'), borderColor: css('--surface'), borderWidth: 2 }, label: { show: true, position: 'top', color: css('--ink'), fontWeight: 600, formatter: (p: { dataIndex: number; value: number }) => (p.dataIndex === last + 1 ? num(p.value, lang.value) : '') } }]
        : []),
    ],
  }
})
</script>

<template>
  <div class="h-72 w-full">
    <VChart :option="option" autoresize />
  </div>
</template>
