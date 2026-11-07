// состояние сервера для плашки по сигналам запросов к API (чистая функция – покрыта тестами):
// ok – сервер ответил (даже ошибкой 4xx); slow – запрос ждёт ответа дольше 2,5 с; waking – прокси Render отвечает
// 502/503/504, пока сервис поднимается; fail – сеть недоступна или вышел срок ожидания
export type ServerStatus = 'unknown' | 'waking' | 'ready' | 'down'
export type ServerSignal = 'ok' | 'slow' | 'waking' | 'fail'

export interface StatusMemory {
  status: ServerStatus
  lastOk: number // когда сервер последний раз ответил
  lastFail: number // когда запрос последний раз упал
}

// сервер отвечал недавно – значит, не спит: один медленный запрос плашку не включает
export const ALIVE_MS = 30_000

// started – когда начался запрос, приславший сигнал. «Медленный» запрос, начатый до последнего падения, плашку не
// меняет: иначе после ошибки зависшие соседние запросы снова включали бы «просыпается», хотя сервер уже не ответил
export function nextStatus(m: StatusMemory, signal: ServerSignal, now: number, started: number): StatusMemory {
  if (signal === 'ok') return { ...m, status: 'ready', lastOk: now }
  if (signal === 'fail') return { ...m, status: now - m.lastOk > ALIVE_MS ? 'down' : m.status, lastFail: now }
  if (now - m.lastOk <= ALIVE_MS) return m
  if (signal === 'waking') return { ...m, status: 'waking' }
  if (started < m.lastFail) return m // slow от запроса, начатого до последнего падения
  return { ...m, status: 'waking' }
}
