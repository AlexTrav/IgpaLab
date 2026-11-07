import type { RouteLocationNormalized, RouterScrollBehavior } from 'vue-router'

type Where = Pick<RouteLocationNormalized, 'path' | 'hash'>

// куда прокрутить после перехода: назад и вперёд – на прежнее место, якорь – к нему, новая страница – наверх.
// Смена только query (ползунки «Быстрого расчёта», вкладки «Исследования») страницу не двигает
export function scrollTarget(to: Where, from: Where, saved: { left: number; top: number } | null) {
  if (saved) return saved
  if (to.hash) return { el: to.hash, top: 80 }
  if (to.path === from.path) return false
  return { top: 0 }
}

export const scrollBehavior: RouterScrollBehavior = (to, from, saved) => scrollTarget(to, from, saved)
