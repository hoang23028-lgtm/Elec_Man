FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY backend/pyproject.toml ./
COPY ai/requirements.txt ./ai-requirements.txt
RUN pip install --upgrade pip && pip install . -r ai-requirements.txt
COPY backend/app ./app
COPY ai ./ai
RUN useradd --system --uid 10001 --create-home worker && chown -R worker:worker /app
USER worker
CMD ["python", "-m", "ai.worker"]
