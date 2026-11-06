.PHONY: build run test clean

IMAGE := igpalab-api

# Git Bash на Windows иначе превращает пути контейнера в пути Windows
export MSYS_NO_PATHCONV=1

# образ собирается из корня репозитория: внутрь попадают igpa, api и артефакты моделей
build:
	docker build -f "$(CURDIR)/Dockerfile" -t $(IMAGE) "$(CURDIR)/.."

# API локально на http://localhost:8000 (документация – /docs)
run: build
	docker run --rm -p 8000:8000 $(IMAGE)

# pytest: все точки API на настоящих артефактах
test: build
	docker run --rm $(IMAGE) pytest -q -p no:cacheprovider tests

# удалить образ
clean:
	docker rmi -f $(IMAGE)
