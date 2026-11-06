.PHONY: build generate csv open test clean

IMAGE := igpalab-data
VERSION ?= v1

# Git Bash на Windows иначе превращает пути контейнера (/repo/data) в пути Windows
export MSYS_NO_PATHCONV=1

# папка data монтируется на запись (результат остаётся в synthetic/), калькулятор igpa – только для чтения
RUN := docker run --rm -v "$(CURDIR):/repo/data" -v "$(CURDIR)/../igpa:/repo/igpa:ro" $(IMAGE)

# собрать образ с зависимостями
build:
	docker build -t $(IMAGE) .

# сгенерировать версию датасета в synthetic/$(VERSION); другие параметры: make generate ARGS="--students 12000 --version v1-12k"
generate: build
	$(RUN) python -m generator generate --version $(VERSION) $(ARGS)

# выгрузить таблицы версии в CSV для просмотра (synthetic/$(VERSION)/csv, в git не идут)
csv: build
	$(RUN) python -m generator csv --dir synthetic/$(VERSION)

# скачать открытые данные для серии S5 (UCI Student Performance) в open/uci, в git не идут
open: build
	$(RUN) python -m generator open

# pytest: инварианты истории и АСУ, формат xlsx, сверка срезов с калькулятором, воспроизводимость
test: build
	$(RUN) pytest

# удалить образ (сгенерированные данные остаются)
clean:
	docker rmi -f $(IMAGE)
