# =============================================================================
# Stage 1 — builder: instala dependencias
# =============================================================================
FROM python:3.13-slim AS builder

WORKDIR /build

# Instala dependencias del sistema necesarias para compilar (si alguna
# extensión nativa lo requiere)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia solo lo necesario para instalar dependencias
COPY pyproject.toml ./

# Instala dependencias en un directorio local (sin toolchain en runtime)
RUN pip install --no-cache-dir --user -e ".[dev]"

# =============================================================================
# Stage 2 — runtime: imagen mínima para producción
# =============================================================================
FROM python:3.13-slim AS runtime

# Variables de entorno de runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/root/.local/bin:${PATH}"

# Dependencias del sistema necesarias en runtime (libpq para asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copia el entorno instalado desde builder
COPY --from=builder /root/.local /root/.local

# Copia el código de la aplicación
COPY app/ /app/app/
COPY alembic.ini /app/alembic.ini
COPY alembic/ /app/alembic/

WORKDIR /app

# Expone el puerto de la API
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()" || exit 1

# Arranca uvicorn con el patrón --factory
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
