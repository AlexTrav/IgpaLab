# Состояние работ (читать первым после перерыва)

Обновлено 07.11.2026, ~09:00. Готово всё по плану pre-project: шаги 1–9, CI/CD, сайт и API работают, черновик статьи (шаг 10) собран в DOCX и PDF на английском и для чтения на русском. Остановились на передаче статьи на вычитку; следующее – список открытых вопросов (пользователь попросит после компакта). Репозиторий: github.com/AlexTrav/IgpaLab (приватный), ветка main; сайт: https://alextrav.github.io/IgpaLab/ (Pages с приватного репозитория, GitHub Pro); API: https://igpalab-backend.onrender.com.

## Готово и запушено

Шаги 1–8: калькулятор `igpa/` (75 тестов), генератор `data/` (v1 на 6000 студентов, 25 тестов), анализ `research/` (6 тестов), модели `model/` (B0, B1, Ridge, RF, CatBoost, Stack, Mean, IGPA-Hybrid; серии S0–S3, S7, S8; рекомендатель; SHAP; 30 тестов), финальные модели `model/artifacts/v1`, API `backend/` (13 тестов). Итоги каждого шага – в [research.md](research.md), решения – в [decisions.md](decisions.md).

## Семь доработок после шага 8 (готовы все)

| Пункт | Что | Код | Команда | Состояние |
| --- | --- | --- | --- | --- |
| 1 | Облегчённые модели сайта по полному протоколу: точность, честность коридоров 10–90%, калибровка риска | `model/forecast/checks.py: light` | `make -C model check NAME=light` | готово: итог в research.md («Доработка 1») |
| 2 | Кривая обучения (250…все студенты, тест 1000 студентов вне обучения) и насыщение на версии v1-12k | `checks.py: learning` | `make -C model check NAME=learning`; для 12k сначала `make -C data generate VERSION=v1-12k ARGS="--students 12000"`, затем `make -C model check NAME=learning VERSION=v1-12k` | готово: research.md («Доработка 2») |
| 3 | Сценарии: «только выгрузка АСУ и GPA» и «малые данные» (магистранты, 1 год истории) | `checks.py: scenarios` | `make -C model check NAME=scenarios` | готово: research.md («Доработка 3») |
| 4 | Семестровый горизонт (наивные: «не изменится» и сезонный) | `checks.py: semester` | `make -C model check NAME=semester` | готово: research.md («Доработка 4») |
| 5 | S5 на открытых данных UCI Student Performance (данные скачаны в `data/open/uci`, в git не идут); OULAD по возможности | `checks.py: open_uci` | `make -C data open`, затем `make -C model check NAME=open-uci` | готово: research.md («Доработка 5»); OULAD не делали |
| 6 | Устойчивость к генератору: (а) v1 с другим seed; (б) версия, откалиброванная под AITU (участие хоть раз: iROS 26%, SSCI 70%; в v1 по всем записям АСУ 47% и 58%); прогнать ключевые модели, сравнить выводы | `config_aitu.yaml`, `checks.py: robust` | models, hybrid, recsys с `VERSION=v1-seed2` и `v1-aitu`, затем `make -C model check NAME=robust` | готово: research.md («Доработка 6») |
| 7 | Контроль моделей с непересекающимися студентами | `make -C model models` с `--disjoint` | `make -C model models ARGS=--disjoint` | готово: research.md («Доработка 7») |

## Шаг 9: сайт и CI/CD (готово 07.11.2026)

- `frontend/`: Vue 3, TypeScript, Tailwind 4, vue-i18n (ru, kk, en), ECharts; 20 тестов Vitest; `make -C frontend test`, `build`, `run`, `dev`. Страницы: главная (живая формула), «Мой портфель», «Студент со стенда», «Быстрый расчёт», «Исследование» (5 вкладок), «О проекте». Дополнительно: View Transitions, «Поделиться» PNG, PWA, экскурсия по портфелю, подсказки «?», анимации. Lighthouse не запускаем (инцидент с диском, см. «Грабли среды»).
- Локальная проверка: `make -C backend run` (API на :8000) и `make -C frontend run API=http://localhost:8000` (сайт на :8080).
- CI: `.github/workflows/ci.yml` – 6 задач в Docker (igpa, data, research, model, backend, frontend). Pages: `pages.yml` после зелёного CI. Render: `render.yaml` (igpalab-backend, free, Frankfurt, autoDeployTrigger checksPass, CORS только alextrav.github.io); сервис создан вручную 07.11.2026: https://igpalab-backend.onrender.com (Frankfurt, Free, Auto-Deploy после CI, Build Filters как в render.yaml).
- После новых проверок моделей: `make -C model export-research` пересобирает только research.json.

## Шаг 10: статья (черновик готов 07.11.2026)

- Папка вне репозитория `pre-project/Статья - IEEE DG 2027/`: `Nerezov_Mukanova_IEEE_DG_2027.docx` и `.pdf` (подаётся, английский, 5 страниц, A4, Times New Roman встроен), `Nerezov_Mukanova_IEEE_DG_2027_RU.docx` и `.pdf` (русский перевод для чтения, тот же формат, рисунки и литература как в оригинале), `Требования/` (официальный шаблон Word с сайта, памятка CMT, шаблон слайдов), `_сборка/` (тексты `content.py` и `content_ru.py`, рисунки `figures.py`, сборка `build.py`, LibreOffice для PDF; README с командами). Требования и авторы – в [conference.md](conference.md).
- Название: «Formula-Aware Forecasting and Recommendation of the Integrated GPA on a Synthetic University Testbed». Авторы: Alexey Nerezov (alexeynerezov@gmail.com, ORCID 0009-0009-6440-311X) и Zhanna Mukanova (zh.mukanova@turan-edu.kz, ORCID 0000-0001-6506-9007), Turan University. 3 рисунка, 3 таблицы, 2 формулы, 17 источников (12 из Scopus или WoS, самоцитирования нет), выходные данные сверены на страницах издателей.
- Формат: двухколоночный шаблон IEEE (так требует конференция), стили и поля шаблона не менялись; после «Abstract» и «Keywords» – «–» вместо длинного тире (правило автора).
- PDF делает LibreOffice в Docker со шрифтами Windows (`-v C:/Windows/Fonts:/usr/share/fonts/windows:ro`); экспорт через Word COM запрещён автоматической проверкой Claude Code.
- Осталось: вычитка автором и научным руководителем; регистрация в CMT и загрузка PDF до 17.12.2026; слайды на английском по шаблону конференции (доклад 15 минут и 5 минут на вопросы).

Сроки: предварительная сдача сайта и статьи – обед 09.11.2026; подача – до 17.12.2026; уведомление – 08.02.2027; финальная версия – 15.02.2027; конференция – 24–26.02.2027, AITU, Астана.

## Не забыть

- Цитировать ближайшую работу: Soltan и др., 2025, Scientific Journal of AITU, DOI 10.37943/23JOZI8138 (см. conference.md).
- Вопросы научному руководителю (Муканова Ж. А.) – questions.md, главный – вопрос 5 (как АСУ считает общий балл).
- Казахские тексты API сверены, но показать носителю.
- Казахские тексты сайта (frontend/src/locales/kk.ts) – тоже показать носителю.

## Грабли среды

- Время в логах моделей – UTC (на 5 часов меньше местного).
- Heredoc в Git Bash портит обратные слэши (`\n` в Python-коде) – такие правки делать через Edit/Write, не через `python - <<EOF`.
- Docker: 6 ядер, 6 ГБ; пути с кириллицей работают через `$(CURDIR)` в Makefile и `pwd -W` в командах.
- Длинные прогоны – в фоне, с логом в `model/results/logs/`.
- 07.11.2026 Chromium в Docker (Lighthouse) падал, и WSL писал дампы в `%LOCALAPPDATA%\Temp\wsl-crashes` – 284 ГБ, диск C: заполнился до нуля. Дампы удалены, в `.wslconfig` `maxCrashDumpCount=0`. Lighthouse в Docker не запускать; перед и после тяжёлых задач – `df -h /c` (правило в глобальном CLAUDE.md).
- Скриншоты Playwright для проверок – в контейнере с `ulimit -c 0`; сайт собирается с API `localhost:8000`, а Playwright подменяет адрес на `host.docker.internal:8000`.
