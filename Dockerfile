# syntax=docker/dockerfile:1

# ---- builder: install python deps into a venv ----
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --upgrade pip && pip install ".[ocr]"

# ---- runtime ----
FROM python:3.12-slim

# libgl1 + libglib2.0-0: required by opencv-python (rapidocr dependency)
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 docparse

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    DOCPARSE_JOBS_DIR=/data/jobs

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY app ./app

RUN mkdir -p /data/jobs && chown -R docparse:docparse /data /app
USER docparse

EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8787/health', timeout=4).status == 200 else 1)"]

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8787"]
