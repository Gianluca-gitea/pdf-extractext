FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libmupdf-dev \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup --home /home/appuser appuser

RUN chown -R appuser:appgroup /app

USER appuser

ENV UV_CACHE_DIR=/tmp/.uv-cache

COPY --chown=appuser:appgroup pyproject.toml uv.lock README.md ./

RUN uv sync --frozen --no-dev --no-cache

ENV PATH="/app/.venv/bin:$PATH"

COPY --chown=appuser:appgroup app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
