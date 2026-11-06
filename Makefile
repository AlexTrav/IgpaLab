.PHONY: test data

# все автотесты
test:
	"$(MAKE)" -C igpa test
	"$(MAKE)" -C data test

# сгенерировать синтетический датасет (data/synthetic/v1)
data:
	"$(MAKE)" -C data generate
