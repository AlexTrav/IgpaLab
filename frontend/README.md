# frontend: сайт IgpaLab

Vue 3, TypeScript, Tailwind CSS 4, vue-i18n (ru, kk, en), Apache ECharts, @vueuse, lucide. Опубликован на https://alextrav.github.io/IgpaLab/ (GitHub Pages после зелёного CI).

## Запуск

Всё в Docker, node_modules на диске не нужен.

```
make -C frontend test                            # 16 тестов Vitest: переводы, формула IGPA, форматирование, плашка сервера
make -C frontend run API=http://localhost:8000   # собранный сайт на http://localhost:8080 (вместе с make -C backend run)
make -C frontend dev                             # dev-сервер Vite на http://localhost:5173 (API – .env.development)
make -C frontend lock                            # обновить package-lock.json после правки package.json
```

Без `API=` сайт собирается с API на Render (https://igpalab-backend.onrender.com).

## Устройство

| Путь | Что там |
| --- | --- |
| `src/views/` | Страницы: главная, «Мой портфель», «Студент со стенда» и карточка студента, «Быстрый расчёт», «Исследование», «О проекте» |
| `src/components/` | Живая формула и полоса IGPA, прогноз «веером», риск, объяснение SHAP, советы, графики исследования, экскурсия, подсказки «?» |
| `src/composables/` | Портфель (хранится только в браузере), справочники АСУ, результаты исследования, тема, язык, состояние сервера |
| `src/api/client.ts` | Запросы к API: плашка «Сервер просыпается», автоповтор при 502–504 от Render |
| `src/utils/` | Формула IGPA, форматирование чисел по языку, карточка «Поделиться», правила плашки сервера |
| `src/locales/` | Тексты на трёх языках (одинаковые ключи проверяет тест) |
| `public/` | Иконки, манифест и service worker (офлайн-режим) |

Цвета данных (GPA, iROS, SSCI, модели) закреплены в `src/style.css` и проверены на различимость при дальтонизме в светлой и тёмной теме.
