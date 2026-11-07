// общее для графиков ECharts: цвета берутся из CSS-переменных текущей темы (палитра проверена валидатором dataviz),
// оси и сетка – приглушённые, подписи – цветом текста, а не цветом серии

export function css(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

export function axisStyle() {
  return {
    axisLine: { lineStyle: { color: css('--axis') } },
    axisTick: { show: false },
    axisLabel: { color: css('--faint'), fontFamily: 'Onest Variable, system-ui, sans-serif', fontSize: 11 },
    splitLine: { lineStyle: { color: css('--grid') } },
  }
}

export function tooltipStyle() {
  return {
    backgroundColor: css('--surface'),
    borderColor: css('--line'),
    textStyle: { color: css('--ink'), fontFamily: 'Onest Variable, system-ui, sans-serif', fontSize: 12 },
    extraCssText: 'border-radius: 12px; box-shadow: 0 10px 30px -12px rgb(18 26 51 / 0.35);',
  }
}

export const reducedMotion = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
