.PHONY: build baselines test clean

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
	$(RUN) python -m forecast --version $(VERSION) --models B0,B1 --name baselines
	$(RUN) python -m forecast --version $(VERSION) --models B0,B1 --name baselines --disjoint

# pytest: нет утечки из будущего, порядок проверок, метрики и статистика
test: build
	$(RUN) pytest

# удалить образ
clean:
	docker rmi -f $(IMAGE)
