"""Convenciones para migraciones Alembic en activia-trace.

Una migración por cambio de schema
    Cada change (C-NN) produce exactamente una migración.  Nunca mezclar
    cambios de schema de diferentes changes en una misma migración.

Nombres de archivos
    ``{NNN}_{descripcion_corta}.py`` donde:

    - ``NNN`` es el número de secuencia (001, 002, …)
    - ``descripcion_corta`` es un slug en inglés del contenido

    Ejemplo::

        backend/alembic/versions/
        001_tenant.py
        002_add_usuarios.py
        003_add_comunicaciones.py

Secuencial e inmutable
    Una vez creada y commiteada, una migración NO se modifica.  Si se necesita
    un cambio de schema posterior, se crea una NUEVA migración con el número
    siguiente.

Upgrade / Downgrade
    Toda migración implementa ``upgrade()`` y ``downgrade()``.  El ciclo
    ``upgrade → downgrade -1 → upgrade`` es idempotente.

Qué SÍ y qué NO va en una migración

    ✅ Tablas nuevas
    ✅ Columnas nuevas
    ✅ Índices, constraints, FKs
    ✅ Seed data de catálogos estáticos (vía ``op.execute``)
    ❌ Data de negocio que evoluciona (va en fixtures / seeds)
    ❌ Cambios en modelos Python (van en code, no en migración)
    ❌ Migraciones que dependen de funciones de BD no estándar

Convención de revisiones
    Usar números secuenciales como ``revision`` (001, 002, …) en lugar de
    hashes aleatorios, para facilitar la lectura del orden.
"""

import re
from pathlib import Path

VERSIONS_DIR = Path(__file__).resolve().parents[2] / "alembic" / "versions"


def validate_migration_revision(revision: str) -> bool:
    """Valida que una revisión Alembic sea un número de 3 dígitos."""
    return bool(re.fullmatch(r"\d{3}", revision))


def get_migration_files() -> list[Path]:
    """Retorna los archivos de migración ordenados por nombre."""
    files = sorted(VERSIONS_DIR.glob("[0-9][0-9][0-9]_*.py"))
    return files


def validate_naming_convention() -> list[str]:
    """Valida que todas las migraciones sigan la convención.

    Returns:
        Lista de mensajes de error (vacía si todo ok).
    """
    errors: list[str] = []
    files = get_migration_files()

    if not files:
        return []

    for idx, fpath in enumerate(files):
        # Verificar que el nombre sea {NNN}_{slug}.py
        if not re.match(r"^\d{3}_.+\.py$", fpath.name):
            errors.append(
                f"Formato de nombre inválido: {fpath.name} "
                f"(se espera NNN_descripcion.py)"
            )
        # Verificar secuencia
        expected_prefix = f"{idx + 1:03d}_"
        if not fpath.name.startswith(expected_prefix):
            errors.append(
                f"Secuencia incorrecta: {fpath.name} debería empezar con "
                f"{expected_prefix}"
            )

    return errors
