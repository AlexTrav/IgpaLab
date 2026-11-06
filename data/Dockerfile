# образ только с зависимостями; генератор, калькулятор igpa и шаблоны АСУ подключаются с хоста
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/repo/igpa:/repo/data
WORKDIR /repo/data

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
