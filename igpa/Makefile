.PHONY: build test clean

IMAGE := igpalab-igpa

# Git Bash на Windows иначе превращает пути контейнера (/repo/igpa) в пути Windows
export MSYS_NO_PATHCONV=1

# код калькулятора и шаблоны АСУ (для сверки справочника) монтируются с хоста только для чтения
RUN := docker run --rm -v "$(CURDIR):/repo/igpa:ro" -v "$(CURDIR)/../data/example:/repo/data/example:ro" $(IMAGE)

# собрать образ с зависимостями
build:
	docker build -t $(IMAGE) .

# pytest: справочник против шаблонов АСУ, правила, расчёт, сверка с EduScore
test: build
	$(RUN) pytest

# удалить образ
clean:
	docker rmi -f $(IMAGE)
