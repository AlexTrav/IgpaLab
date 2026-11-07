import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import { scrollBehavior } from './scroll'

// главная грузится сразу, остальные страницы – отдельными чанками при первом переходе
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/portfolio', name: 'portfolio', component: () => import('../views/PortfolioView.vue') },
    { path: '/stand', name: 'stand', component: () => import('../views/StandView.vue') },
    { path: '/stand/:id', name: 'student', component: () => import('../views/StudentView.vue'), props: true },
    { path: '/quick', name: 'quick', component: () => import('../views/QuickView.vue') },
    { path: '/research', name: 'research', component: () => import('../views/ResearchView.vue') },
    { path: '/about', name: 'about', component: () => import('../views/AboutView.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior,
})

export default router
