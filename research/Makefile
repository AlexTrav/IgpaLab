.PHONY: build report test clean

IMAGE := igpalab-research
VERSION ?= v1

# Git Bash на Windows иначе превращает пути контейнера (/repo/research) в пути Windows
export MSYS_NO_PATHCONV=1

# папка research на запись (отчёт в results/), калькулятор и датасет – только для чтения
RUN := docker run --rm -v "$(CURDIR):/repo/research" -v "$(CURDIR)/../igpa:/repo/igpa:ro" \
	-v "$(CURDIR)/../data/synthetic:/repo/data/synthetic:ro" $(IMAGE)

# собрать образ с зависимостями
build:
	docker build -t $(IMAGE) .

# отчёт, числа и рисунки ru/en по версии датасета: results/$(VERSION)
report: build
	$(RUN) python -m analysis --version $(VERSION)

# pytest: панель студент × год собрана без сдвигов, расчёты сходятся со срезами
test: build
	$(RUN) pytest

# удалить образ
clean:
	docker rmi -f $(IMAGE)
