import type { AppLocale, Calc, Meta, Portfolio, PortfolioIn, RecordIn, ResearchRaw, RulesCode, Student, StudentsPage } from '../types'
import type { ServerSignal } from '../utils/serverStatus'

// адрес API: в dev – .env.development, в сборке – аргумент Docker (по умолчанию API на Render)
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'https://igpalab-backend.onrender.com'

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
// started – когда начался запрос (см. utils/serverStatus.ts)
let onServerSignal: (signal: ServerSignal, started: number) => void = () => {}
export function listenServer(listener: (signal: ServerSignal, started: number) => void) {
  onServerSignal = listener
}

// пока прокси Render отвечает 502/503/504 (сервис поднимается), запрос сам повторяется раз в 3 с до общего срока
const RETRY_MS = 3000
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

export async function request<T>(path: string, body?: unknown, timeoutMs = TIMEOUT_MS): Promise<T> {
  const started = Date.now()
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  const slow = setTimeout(() => onServerSignal('slow', started), SLOW_AFTER_MS)
  let res: Response
  try {
    for (;;) {
      res = await fetch(`${API_BASE}${path}`, {
        method: body === undefined ? 'GET' : 'POST',
        headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: controller.signal,
      })
      if (!WAKING_STATUSES.has(res.status)) break
      onServerSignal('waking', started)
      if (Date.now() - started + RETRY_MS >= timeoutMs) {
        onServerSignal('fail', started)
        throw new ApiError('waking', res.status)
      }
      await sleep(RETRY_MS)
    }
  } catch (err) {
    if (err instanceof ApiError) throw err
    onServerSignal('fail', started)
    throw new ApiError((err as Error).name === 'AbortError' ? 'timeout' : 'network')
  } finally {
    clearTimeout(timer)
    clearTimeout(slow)
  }
  onServerSignal('ok', started) // сервер ответил – даже ошибкой 4xx, значит, он не спит
  if (!res.ok) throw new ApiError(`http_${res.status}`, res.status)
  return res.json() as Promise<T>
}

export const api = {
  health: () => request<{ status: string }>('/api/health'),
  meta: (lang: AppLocale) => request<Meta>(`/api/meta?lang=${lang}`),
  calc: (gpa: number, records: RecordIn[], rules: RulesCode, lang: AppLocale) =>
    request<Calc>('/api/calc', { gpa, records, rules, lang }),
  portfolio: (body: PortfolioIn) => request<Portfolio>('/api/portfolio', body),
  students: (params: { q?: string; faculty?: string; level?: string; current?: boolean; limit?: number; offset?: number }) => {
    const query = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== '') query.set(k, String(v))
    return request<StudentsPage>(`/api/students?${query}`)
  },
  student: (id: string, rules: RulesCode, lang: AppLocale) =>
    request<Student>(`/api/students/${encodeURIComponent(id)}?rules=${rules}&lang=${lang}`),
  research: (lang: AppLocale) => request<ResearchRaw>(`/api/research?lang=${lang}`),
}
