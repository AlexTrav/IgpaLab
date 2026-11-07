<script setup lang="ts">
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, MarkLineComponent, TooltipComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { SVGRenderer } from 'echarts/renderers'
import { computed } from 'vue'
import VChart from 'vue-echarts'
import 'vue-echarts/style.css'
import { useI18n } from 'vue-i18n'
import { useTheme } from '../../composables/useTheme'
import type { AppLocale, ResearchRow } from '../../types'
import { axisStyle, css, reducedMotion, tooltipStyle } from '../../utils/chart'
import { int, num } from '../../utils/format'

use([LineChart, GridComponent, LegendComponent, MarkLineComponent, TooltipComponent, SVGRenderer])

// кривая обучения: MAE от числа студентов в обучении (среднее по повторам), пунктир – B0
const props = defineProps<{ rows: ResearchRow[] }>()
const { t, locale } = useI18n()
const { theme } = useTheme()
const lang = computed(() => locale.value as AppLocale)

const option = computed(() => {
  void theme.value
  const sizes = [...new Set(props.rows.filter((r) => r.model !== 'B0').map((r) => Number(r.students)))].sort((a, b) => a - b)
  const mean = (model: string, n: number) => {
    const xs = props.rows.filter((r) => r.model === model && Number(r.students) === n).map((r) => Number(r.mae))
    return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null
  }
  const b0 = Number(props.rows.find((r) => r.model === 'B0')?.mae)
  const color = { CatBoost: css('--series-1'), Ridge: css('--series-2') } as const
  return {
    animation: !reducedMotion(),
    grid: { left: 52, right: 24, top: 34, bottom: 32 },
    legend: { top: 0, left: 0, textStyle: { color: css('--muted'), fontSize: 12 }, itemWidth: 16, itemHeight: 8 },
    xAxis: { type: 'category', data: sizes.map((n) => int(n, lang.value)), ...axisStyle(), splitLine: { show: false }, name: '', boundaryGap: false },
    // линия B0 должна попасть в шкалу: ECharts не учитывает markLine при подборе границ
    yAxis: { type: 'value', scale: true, max: (v: { max: number }) => +(Math.max(v.max, Number.isFinite(b0) ? b0 : 0) + 0.002).toFixed(3), ...axisStyle(), axisLabel: { ...axisStyle().axisLabel, formatter: (v: number) => num(v, lang.value, 3) } },
    tooltip: { trigger: 'axis', ...tooltipStyle(), valueFormatter: (v: number) => num(v, lang.value, 4) },
    series: (['CatBoost', 'Ridge'] as const).map((m, i) => ({
      name: m,
      type: 'line',
      data: sizes.map((n) => mean(m, n)),
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: { width: 2.5, color: color[m] },
      itemStyle: { color: color[m] },
      ...(i === 0 && Number.isFinite(b0)
        ? { markLine: { symbol: 'none', silent: true, lineStyle: { type: 'dashed', color: css('--faint') }, label: { formatter: `B0 ${num(b0, lang.value, 3)}`, color: css('--faint'), position: 'insideEndTop' }, data: [{ yAxis: b0 }] } }
        : {}),
    })),
  }
})
</script>

<template>
  <div class="h-64 w-full" role="img" :aria-label="t('research.learningAria')">
    <VChart :option="option" autoresize />
  </div>
</template>
