.PHONY: build baselines models series hybrid extra review transfer stress advice hybrid-refresh recsys export export-research check test clean

IMAGE := igpalab-model
VERSION ?= v1

# Git Bash на Windows иначе превращает пути контейнера (/repo/model) в пути Windows
export MSYS_NO_PATHCONV=1

# папка model на запись (результаты в results/); igpa, генератор и датасет – только для чтения
RUN := docker run --rm -v "$(CURDIR):/repo/model" -v "$(CURDIR)/../igpa:/repo/igpa:ro" \
	-v "$(CURDIR)/../data:/repo/data:ro" $(IMAGE)

# собрать образ с зависимостями
build:
	docker build -t $(IMAGE) .

# базовые уровни B0 и B1 по протоколу и контрольный прогон с непересекающимися студентами
baselines: build
	$(RUN) python -m forecast --version $(VERSION) --name baselines
	$(RUN) python -m forecast --version $(VERSION) --name baselines --disjoint

# pytest: нет утечки из будущего, порядок проверок, метрики и статистика
test: build
	$(RUN) pytest

# удалить образ
clean:
	docker rmi -f $(IMAGE)

# три алгоритма, ансамбли и контроль прогноза уровня: results/v1/models; контроль с непересекающимися студентами: make models ARGS=--disjoint
models: build
	$(RUN) python -m forecast --version $(VERSION) --name models $(ARGS)

# серии S0–S3 на CatBoost: вклад групп признаков: results/v1/series
series: build
	$(RUN) python -m forecast --version $(VERSION) --name series

# своя модель IGPA-Hybrid против B0, CatBoost и стекинга (их прогнозы из прогона models) и серия S8
hybrid: build
	$(RUN) python -m forecast --version $(VERSION) --name hybrid

# базовые уровни B2–B6 по плану доработки статьи и Huber: results/v1/extra
extra: build
	$(RUN) python -m forecast --version $(VERSION) --name extra

# после нового прогона models: S8 (смена правила) и сводка hybrid с новыми CatBoost и Stack, без переобучения гибрида
hybrid-refresh: build
	$(RUN) python -m forecast --version $(VERSION) --name hybrid-refresh

# по рецензии статьи: риск, калибровка, парные разности, подгруппы, пороги, коридор против conformal (после extra)
review: build
	$(RUN) python -m forecast --version $(VERSION) --name review

# перенос: обучение без факультета или только на бакалавриате, проверка на этой группе: results/v1/transfer
transfer: build
	$(RUN) python -m forecast --version $(VERSION) --name transfer

# смена правила с изменением поведения (+30% разовых SSCI в 2025/26): results/v1/stress (после models и hybrid)
stress: build
	$(RUN) python -m forecast --version $(VERSION) --name stress

# ретроспективная оценка советов: выполнение, покрытие, regret, типы действий: results/v1/advice
advice: build
	$(RUN) python -m forecast --version $(VERSION) --name advice

# шаг 7: SHAP, восстановление эффектов, серия S7, проверка рекомендаций: results/v1/recsys
recsys: build
	$(RUN) python -m forecast --version $(VERSION) --name recsys

# шаг 8: финальные модели и данные для сайта: artifacts/v1; make export-research – только research.json (без обучения)
export-research: build
	$(RUN) python -m forecast --version $(VERSION) --name export-research

export: build
	$(RUN) python -m forecast --version $(VERSION) --name export

# доработки: make -C model check NAME=light (результаты results/v1/checks)
check: build
	$(RUN) python -m forecast --version $(VERSION) --name check-$(NAME)
