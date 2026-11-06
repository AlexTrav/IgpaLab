# образ только с зависимостями; код калькулятора и шаблоны АСУ подключаются с хоста
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/repo/igpa
WORKDIR /repo/igpa

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
