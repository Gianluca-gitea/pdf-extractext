FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md .

RUN uv pip install --system -e .

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
