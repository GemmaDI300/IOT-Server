# ── Backend Dockerfile (FastAPI + SQLite) ──
FROM python:3.12-slim AS base

# Instalar uv para gestión rápida de dependencias
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copiar solo archivos de dependencias primero (cache de capas)
COPY pyproject.toml uv.lock ./

# Instalar dependencias (sin dev, cache de pip)
RUN uv sync --frozen --no-dev --no-install-project

# Copiar el código fuente
COPY app/ ./app/
COPY seed_admin.py docker_entrypoint.py ./

# Crear directorio para la base de datos SQLite
RUN mkdir -p /app/data

# Usuario no root por seguridad
RUN adduser --disabled-password --no-create-home appuser \
    && chown -R appuser:appuser /app
USER appuser

# Desactivar caché de uv (no necesario en runtime)
ENV UV_NO_CACHE=1

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/docs')" || exit 1

# Entrypoint: crear tablas + seed + servidor
CMD ["uv", "run", "python", "docker_entrypoint.py"]
