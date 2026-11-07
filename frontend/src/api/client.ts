import type { AppLocale, Calc, Meta, Portfolio, PortfolioIn, RecordIn, Research, RulesCode, Student, StudentsPage } from '../types'

// адрес API: в dev – .env.development, в сборке – аргумент Docker (по умолчанию API на Render)
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'https://igpalab-api.onrender.com'

// бесплатный Render засыпает: пробуждение и загрузка моделей занимают около минуты – ждём дольше обычного
const TIMEOUT_MS = 90_000
// если ответа нет дольше этого – скорее всего, сервер просыпается: показываем плашку
const SLOW_AFTER_MS = 2500
// пока Render будит сервис, его прокси отвечает 502/503/504
const WAKING_STATUSES = new Set([502, 503, 504])

export class ApiError extends Error {
  code: string
  status: number

  constructor(code: string, status = 0) {
    super(code)
    this.name = 'ApiError'
    this.code = code
    this.status = status
  }
}

// каждый запрос сообщает, в каком состоянии сервер: плашка «Сервер просыпается…» видна на любой странице
export type ServerSignal = 'slow' | 'ok' | 'fail'
let onServerSignal: (signal: ServerSignal) => void = () => {}
export function listenServer(listener: (signal: ServerSignal) => void) {
  onServerSignal = listener
}

export async function request<T>(path: string, body?: unknown, timeoutMs = TIMEOUT_MS): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  const slow = setTimeout(() => onServerSignal('slow'), SLOW_AFTER_MS)
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: body === undefined ? 'GET' : 'POST',
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    })
  } catch (err) {
    onServerSignal('fail')
    throw new ApiError((err as Error).name === 'AbortError' ? 'timeout' : 'network')
  } finally {
    clearTimeout(timer)
    clearTimeout(slow)
  }
  if (WAKING_STATUSES.has(res.status)) {
    onServerSignal('fail')
    throw new ApiError('waking', res.status)
  }
  onServerSignal('ok') // сервер ответил – даже ошибкой 4xx, значит, он не спит
  if (!res.ok) throw new ApiError(`http_${res.status}`, res.status)
  return res.json() as Promise<T>
}

export const api = {
  health: () => request<{ status: string }>('/api/health'),
  meta: (lang: AppLocale) => request<Meta>(`/api/meta?lang=${lang}`),
  calc: (gpa: number, records: RecordIn[], rules: RulesCode, lang: AppLocale) =>
    request<Calc>('/api/calc', { gpa, records, rules, lang }),
  portfolio: (body: PortfolioIn) => request<Portfolio>('/api/portfolio', body),
  students: (params: { q?: string; faculty?: string; level?: string; limit?: number; offset?: number }) => {
    const query = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== '') query.set(k, String(v))
    return request<StudentsPage>(`/api/students?${query}`)
  },
  student: (id: string, rules: RulesCode, lang: AppLocale) =>
    request<Student>(`/api/students/${encodeURIComponent(id)}?rules=${rules}&lang=${lang}`),
  research: () => request<Research>('/api/research'),
}
