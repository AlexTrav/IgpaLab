import { nextTick } from 'vue'
import type { Router } from 'vue-router'

// переходы между страницами через View Transitions API: старая страница растворяется, новая проявляется, шапка
// остаётся на месте (view-transition-name в style.css). Где API нет или включено «уменьшить движение» – обычный
// переход Vue в App.vue
export const viewTransitions =
  typeof document !== 'undefined' && 'startViewTransition' in document && !window.matchMedia('(prefers-reduced-motion: reduce)').matches

export function installViewTransitions(router: Router) {
  if (!viewTransitions) return
  let finish: (() => void) | null = null
  router.beforeResolve((to, from) => {
    if (to.path === from.path || from.matched.length === 0) return
    document.documentElement.classList.add('vt-page') // анимация страниц, а не смены темы (useTheme)
    return new Promise<void>((ready) => {
      const transition = document.startViewTransition(
        () =>
          new Promise<void>((done) => {
            finish = done
            ready()
          }),
      )
      transition.finished.finally(() => document.documentElement.classList.remove('vt-page'))
    })
  })
  router.afterEach(() => {
    nextTick(() => {
      finish?.()
      finish = null
    })
  })
}
