FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*
COPY backend/pyproject.toml ./
COPY ai/requirements.txt ./ai-requirements.txt
RUN mkdir -p app && touch app/__init__.py \
    && pip install --no-compile . -r ai-requirements.txt \
    && pip install --no-compile --no-deps rapidocr-onnxruntime==1.4.4
COPY backend/app ./app
COPY ai ./ai
RUN useradd --system --uid 10001 --create-home worker && chown -R worker:worker /app
USER worker
CMD ["python", "-m", "ai.worker"]
