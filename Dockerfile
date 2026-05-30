FROM python:3.14-slim AS test
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e ".[dev]"
RUN black --check .
RUN ruff check .
RUN mypy camgrab/
RUN pytest tests/ -v

FROM ubuntu:24.04 AS final
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    imagemagick \
    rsync \
    python3 \
    python3-pip \
    python3-venv \
    fonts-freefont-ttf \
    tzdata \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=test /app/camgrab ./camgrab
COPY --from=test /app/pyproject.toml .
RUN python3 -m venv /venv && /venv/bin/pip install --no-cache-dir .
ENTRYPOINT ["/venv/bin/python", "-m", "camgrab"]
