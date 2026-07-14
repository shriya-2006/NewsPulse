# syntax=docker/dockerfile:1

FROM python:3.12-slim

# WeasyPrint needs Pango/Cairo/GDK-Pixbuf at runtime — these are native
# libraries pip can't install. This is the same GTK3 runtime dependency
# documented in README.md for local Windows setup, just the Linux
# equivalent baked into the image.
# fonts-noto-core/fonts-noto-ui-core specifically provide Devanagari
# (Hindi) and Telugu glyphs with correct conjunct/matra shaping — without
# them, Hindi/Telugu report PDFs render as missing glyphs or garbled
# text on a fresh container that has no other font package supplying
# those scripts.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf2.0-0 \
        libcairo2 \
        libffi-dev \
        shared-mime-info \
        fonts-liberation \
        fonts-noto-core \
        fonts-noto-ui-core \
        default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/generated_reports

# Railway sets $PORT at runtime and expects the app to bind to it —
# 8000 is only a local-dev fallback for `docker run` without Railway.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
