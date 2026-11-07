// service worker IgpaLab: сайт открывается и без сети – с последними сохранёнными данными стенда и исследования.
// Оболочка (index.html) и GET-ответы API – «сначала сеть, при ошибке – кэш»; файлы сборки с хэшем в имени не
// меняются – «сначала кэш». POST-расчёты (портфель, калькулятор) не кэшируются: без сети они честно недоступны
const SHELL = 'igpalab-shell-v1'
const DATA = 'igpalab-data-v1'
const API = 'https://igpalab-api.onrender.com/api/'

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(SHELL).then((cache) => cache.addAll(['./', './index.html'])))
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => ![SHELL, DATA].includes(k)).map((k) => caches.delete(k)))),
  )
  self.clients.claim()
})

// запрос к сети ждёт не дольше 90 с: бесплатный Render просыпается и загружает модели около минуты;
// по истечении – последний сохранённый ответ
const NETWORK_TIMEOUT_MS = 90_000

async function networkFirst(request, cacheName, fallback) {
  const cache = await caches.open(cacheName)
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), NETWORK_TIMEOUT_MS)
  try {
    const response = await fetch(request, { signal: controller.signal })
    if (response.ok) cache.put(fallback ?? request, response.clone())
    return response
  } catch (error) {
    const cached = await cache.match(fallback ?? request)
    if (cached) return cached
    throw error
  } finally {
    clearTimeout(timer)
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(SHELL)
  const cached = await cache.match(request)
  if (cached) return cached
  const response = await fetch(request)
  if (response.ok) cache.put(request, response.clone())
  return response
}

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return
  const url = new URL(request.url)
  // /api/health будит сервер – его не кэшируем, чтобы плашка «просыпается» была честной
  if (request.url.startsWith(API) && !url.pathname.endsWith('/health')) {
    event.respondWith(networkFirst(request, DATA))
  } else if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request, SHELL, './index.html'))
  } else if (url.origin === self.location.origin && url.pathname.includes('/assets/')) {
    event.respondWith(cacheFirst(request))
  }
})
