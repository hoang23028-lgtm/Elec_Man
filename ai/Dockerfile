FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libgl1 tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*
COPY backend/pyproject.toml ./
COPY ai/requirements.txt ./ai-requirements.txt
COPY backend/app ./app
RUN pip install --upgrade pip && pip install . -r ai-requirements.txt
COPY ai ./ai
RUN useradd --system --uid 10001 --create-home worker && chown -R worker:worker /app
USER worker
CMD ["python", "-m", "ai.worker"]
