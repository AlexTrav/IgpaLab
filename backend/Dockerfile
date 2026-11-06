# образ API; собирается из корня репозитория (make -C backend build, Render): нужны калькулятор igpa,
# код API и артефакты моделей model/artifacts/v1 (состав контекста – .dockerignore в корне)
FROM python:3.12-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY igpa/igpa ./igpa
COPY model/artifacts/v1 ./artifacts
COPY backend/api ./api
COPY backend/tests ./tests

# CatBoost в один поток: на бесплатном Render доля одного ядра
ENV ARTIFACTS=/app/artifacts PYTHONPATH=/app PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1
# Render передаёт порт в переменной PORT
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
