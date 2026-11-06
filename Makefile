.PHONY: test data report export api

# все автотесты
test:
	"$(MAKE)" -C igpa test
	"$(MAKE)" -C data test
	"$(MAKE)" -C research test
	"$(MAKE)" -C model test
	"$(MAKE)" -C backend test

# сгенерировать синтетический датасет (data/synthetic/v1)
data:
	"$(MAKE)" -C data generate

# анализ данных: отчёт и рисунки research/results/v1
report:
	"$(MAKE)" -C research report

# финальные модели и данные для сайта: model/artifacts/v1
export:
	"$(MAKE)" -C model export

# API локально на http://localhost:8000
api:
	"$(MAKE)" -C backend run
