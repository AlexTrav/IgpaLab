import { ref } from 'vue'
import { api, listenServer } from '../api/client'
import { nextStatus, type StatusMemory } from '../utils/serverStatus'

export type { ServerStatus } from '../utils/serverStatus'

// одно состояние на весь сайт: плашку обновляет любой запрос к API (правила – utils/serverStatus.ts)
let memory: StatusMemory = { status: 'unknown', lastOk: -Infinity, lastFail: -Infinity }
const status = ref(memory.status)
let pending: Promise<void> | null = null

listenServer((signal, started) => {
  memory = nextStatus(memory, signal, Date.now(), started)
  status.value = memory.status
})

export function useServerStatus() {
  // будит API при открытии сайта и по кнопке «Повторить»: бесплатный Render засыпает через 15 минут без запросов
  function wake(): Promise<void> {
    pending ??= api
      .health()
      .then(() => {})
      .catch(() => {})
      .finally(() => {
        pending = null
      })
    return pending
  }
  return { status, wake }
}
