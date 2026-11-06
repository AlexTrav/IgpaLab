# образ только с зависимостями; код моделей, калькулятор igpa, генератор (для state_at) и датасет – с хоста
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/repo/igpa:/repo/data:/repo/model MPLCONFIGDIR=/tmp/mpl \
    OMP_NUM_THREADS=4
WORKDIR /repo/model

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
