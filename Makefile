.PHONY: test data report

# все автотесты
test:
	"$(MAKE)" -C igpa test
	"$(MAKE)" -C data test
	"$(MAKE)" -C research test

# сгенерировать синтетический датасет (data/synthetic/v1)
data:
	"$(MAKE)" -C data generate

# анализ данных: отчёт и рисунки research/results/v1
report:
	"$(MAKE)" -C research report
