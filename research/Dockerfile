# образ только с зависимостями; код анализа, калькулятор igpa и датасет подключаются с хоста
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/repo/igpa:/repo/research MPLCONFIGDIR=/tmp/mpl
WORKDIR /repo/research

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
