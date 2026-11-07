// карточка «Поделиться» 1200×630 (размер превью в соцсетях): IGPA сейчас с полосой формулы, прогноз на следующий
// год с коридором и риском, главный совет – рисуется на canvas в браузере, без сервера; все подписи – уже на языке сайта
export interface ShareCard {
  title: string // «Мой IGPA · Положение»
  igpa: string
  parts: { gpa: number; iros: number; ssci: number } // вклады на шкале 0–4
  legend: [string, string, string] // «GPA 1,55» и т. п.
  forecastLabel: string
  forecast: string
  band: string
  risk: string
  advice: string
  footer: string
  url: string
}

const W = 1200
const H = 630
const COLORS = { gpa: '#3d86ea', iros: '#2ec4b6', ssci: '#f08a4b' }

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath()
  ctx.roundRect(x, y, w, h, r)
}

// перенос строки по словам в заданную ширину, не больше maxLines строк
function wrap(ctx: CanvasRenderingContext2D, text: string, width: number, maxLines: number): string[] {
  const lines: string[] = []
  let line = ''
  for (const word of text.split(' ')) {
    const test = line ? `${line} ${word}` : word
    if (ctx.measureText(test).width > width && line) {
      lines.push(line)
      line = word
    } else line = test
  }
  if (line) lines.push(line)
  if (lines.length > maxLines) {
    lines.length = maxLines
    lines[maxLines - 1] = `${lines[maxLines - 1].replace(/\s+\S*$/, '')}…`
  }
  return lines
}

export async function drawCard(card: ShareCard): Promise<Blob> {
  await document.fonts?.ready
  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')!
  const font = (weight: number, size: number) => `${weight} ${size}px 'Onest Variable', system-ui, sans-serif`

  // фон: глубокий синий с «миллиметровкой» и мягким свечением
  const bg = ctx.createLinearGradient(0, 0, W, H)
  bg.addColorStop(0, '#16245e')
  bg.addColorStop(1, '#0a0e1c')
  ctx.fillStyle = bg
  ctx.fillRect(0, 0, W, H)
  ctx.strokeStyle = 'rgba(255,255,255,0.05)'
  ctx.lineWidth = 1
  for (let x = 0; x < W; x += 40) {
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, H)
    ctx.stroke()
  }
  for (let y = 0; y < H; y += 40) {
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(W, y)
    ctx.stroke()
  }
  const glow = ctx.createRadialGradient(980, 120, 10, 980, 120, 420)
  glow.addColorStop(0, 'rgba(234,176,79,0.28)')
  glow.addColorStop(1, 'rgba(234,176,79,0)')
  ctx.fillStyle = glow
  ctx.fillRect(0, 0, W, H)

  // знак и заголовок
  roundRect(ctx, 64, 56, 48, 48, 12)
  ctx.fillStyle = '#2c4bc2'
  ctx.fill()
  const bars: [number, number, number, string][] = [
    [75, 82, 12, COLORS.ssci],
    [85, 75, 19, '#5fd3c9'],
    [95, 67, 27, '#ffffff'],
  ]
  for (const [x, y, h, color] of bars) {
    roundRect(ctx, x, y, 7, h, 2)
    ctx.fillStyle = color
    ctx.fill()
  }
  ctx.fillStyle = '#ffffff'
  ctx.font = font(700, 30)
  ctx.fillText('IgpaLab', 128, 91)
  ctx.font = font(500, 26)
  ctx.fillStyle = 'rgba(255,255,255,0.7)'
  ctx.fillText(card.title, 64, 158)

  // IGPA сейчас
  ctx.fillStyle = '#ffffff'
  ctx.font = font(700, 150)
  ctx.fillText(card.igpa, 56, 300)
  const w = ctx.measureText(card.igpa).width
  ctx.font = font(500, 40)
  ctx.fillStyle = 'rgba(255,255,255,0.55)'
  ctx.fillText('/ 4', 72 + w, 296)

  // полоса формулы 0–4
  const barX = 64
  const barW = 560
  const barY = 336
  roundRect(ctx, barX, barY, barW, 22, 11)
  ctx.fillStyle = 'rgba(255,255,255,0.12)'
  ctx.fill()
  let x = barX
  for (const key of ['gpa', 'iros', 'ssci'] as const) {
    const width = (Math.max(0, Math.min(4, card.parts[key])) / 4) * barW
    if (width < 1) continue
    roundRect(ctx, x, barY, Math.max(width - 2, 2), 22, 6)
    ctx.fillStyle = COLORS[key]
    ctx.fill()
    x += width
  }
  ctx.font = font(500, 22)
  let lx = barX
  card.legend.forEach((text, i) => {
    const color = [COLORS.gpa, COLORS.iros, COLORS.ssci][i]
    ctx.fillStyle = color
    ctx.beginPath()
    ctx.arc(lx + 7, barY + 58, 7, 0, Math.PI * 2)
    ctx.fill()
    ctx.fillStyle = 'rgba(255,255,255,0.85)'
    ctx.fillText(text, lx + 22, barY + 66)
    lx += ctx.measureText(text).width + 56
  })

  // прогноз справа
  roundRect(ctx, 690, 200, 446, 250, 28)
  ctx.fillStyle = 'rgba(255,255,255,0.08)'
  ctx.fill()
  ctx.font = font(500, 24)
  ctx.fillStyle = 'rgba(255,255,255,0.7)'
  ctx.fillText(card.forecastLabel, 722, 248)
  ctx.font = font(700, 84)
  ctx.fillStyle = '#ffffff'
  ctx.fillText(card.forecast, 718, 336)
  ctx.font = font(500, 26)
  ctx.fillStyle = 'rgba(255,255,255,0.85)'
  ctx.fillText(card.band, 722, 382)
  ctx.fillStyle = '#eab04f'
  ctx.fillText(card.risk, 722, 424)

  // совет и подвал
  ctx.font = font(500, 24)
  ctx.fillStyle = 'rgba(255,255,255,0.9)'
  wrap(ctx, card.advice, W - 128, 2).forEach((line, i) => ctx.fillText(line, 64, 500 + i * 32))
  ctx.font = font(400, 20)
  ctx.fillStyle = 'rgba(255,255,255,0.55)'
  ctx.fillText(card.footer, 64, H - 30)
  const urlWidth = ctx.measureText(card.url).width
  ctx.fillText(card.url, W - 64 - urlWidth, H - 30)

  return new Promise((resolve) => canvas.toBlob((blob) => resolve(blob!), 'image/png'))
}

// на телефоне – системное меню «Поделиться» с файлом, на компьютере – скачивание PNG
export async function shareCard(blob: Blob, name: string, title: string): Promise<void> {
  const file = new File([blob], name, { type: 'image/png' })
  const touch = window.matchMedia('(pointer: coarse)').matches
  if (touch && navigator.canShare?.({ files: [file] })) {
    try {
      await navigator.share({ files: [file], title })
    } catch {
      // пользователь закрыл меню – ничего не делаем
    }
    return
  }
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = name
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
