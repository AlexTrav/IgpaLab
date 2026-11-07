import type { AppLocale } from '../types'

// числа по правилам языка: десятичная запятая для русского и казахского, точка для английского.
// Chromium не знает kk-KZ для чисел – казахский форматируется как русский (тот же разделитель и пробел в тысячах)
const TAG: Record<AppLocale, string> = { ru: 'ru-RU', kk: 'ru-RU', en: 'en-US' }

export function num(value: number | null | undefined, locale: AppLocale, digits = 2): string {
  if (value == null || !Number.isFinite(value)) return '–'
  return new Intl.NumberFormat(TAG[locale], { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value)
}

export function int(value: number | null | undefined, locale: AppLocale): string {
  if (value == null || !Number.isFinite(value)) return '–'
  return new Intl.NumberFormat(TAG[locale], { maximumFractionDigits: 0 }).format(value)
}

// доля 0–1 в проценты: 0.234 → «23%»
export function pct(value: number | null | undefined, locale: AppLocale, digits = 0): string {
  if (value == null || !Number.isFinite(value)) return '–'
  return `${num(value * 100, locale, digits)}%`
}

// со знаком: +0,10 / −0,04 (минус – настоящий знак минуса)
export function signed(value: number | null | undefined, locale: AppLocale, digits = 2): string {
  if (value == null || !Number.isFinite(value)) return '–'
  const s = num(Math.abs(value), locale, digits)
  return value > 0 ? `+${s}` : value < 0 ? `−${s}` : s
}
