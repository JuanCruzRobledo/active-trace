"""Seed script para desarrollo — unifica la creación de datos de prueba.

Crea (si no existen):
  • Tenant de desarrollo (id: 00000000-0000-0000-0000-000000000001)
  • Roles: ADMIN, PROFESOR, TUTOR, COORDINADOR, ALUMNO
  • Permisos globales del sistema + asignación a roles
  • admin@trace.dev / Admin123456!  (roles: ADMIN, PROFESOR)
  • target@test.com  / Target123456! (rol: PROFESOR)
  • admin2@test.com  / Admin123456!  (rol: ADMIN)
  • Estructura académica: carrera, 3 materias, cohorte
  • Asignaciones: target@test.com → AM-I, admin@trace.dev → AM-I, FIS-I, PRO-I
  • Umbrales para todas las asignaciones
  • 3 alumnos (juan, maria, carlos) con calificaciones en las 3 materias
  • Slot recurrente + 4 instancias de encuentro
  • 1 guardia de ejemplo
  • 3 tareas internas (Pendiente, En progreso, Resuelta)
  • 2 avisos (1 Global, 1 PorMateria)
  • 1 evaluación (Coloquio para AM-I)
  • 3 fechas académicas (Parcial, TP, Coloquio)
  • 2 programas de materia (AM-I, FIS-I)
  • 1 comunicación de bienvenida
  • 1 hilo de mensajería con 2 mensajes
  • Salarios base (5 roles) + plus (5 combinaciones)
  • 1 liquidación de ejemplo

Idempotente: se puede ejecutar N veces sin duplicar datos.

Uso:
    cd backend
    python scripts/seed.py

Requiere:
    - Variables de entorno en .env (DATABASE_URL, ENCRYPTION_KEY, etc.)
    - Base de datos migrada (alembic upgrade head)
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from sqlalchemy import select, text

from app.core.config import Settings
from app.core.database import Base, close_engine, get_session_maker, init_engine
from app.core.encryption import EncryptionService
from app.core.security import hash_password
from app.models.asignacion import Asignacion
from app.models.calificacion import Calificacion
from app.models.entrada_padron import EntradaPadron
from app.models.permiso import Permiso
from app.models.umbral_materia import UmbralMateria
from app.models.usuario import Usuario
from app.models.version_padron import VersionPadron
from app.models.aviso import Aviso
from app.models.comunicacion import Comunicacion
from app.models.evaluacion import Evaluacion
from app.models.tarea import Tarea
from app.models.programa_materia import ProgramaMateria
from app.models.fecha_academica import FechaAcademica
from app.models.mensaje import MensajeHilo, Mensaje
from app.repositories.user_repository import UserRepository

# ── Constantes ──────────────────────────────────────────────────────────

DEV_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime.now(UTC)

ROLES = [
    ("ADMIN", "Administrador del sistema"),
    ("PROFESOR", "Profesor/docente"),
    ("TUTOR", "Tutor"),
    ("COORDINADOR", "Coordinador académico"),
    ("ALUMNO", "Alumno"),
]

PERMISOS = [
    ("admin:gestionar-usuarios", "Gestionar usuarios del sistema"),
    ("atrasados:ver", "Ver análisis de atrasados y reportes"),
    ("calificaciones:importar", "Importar calificaciones desde Moodle/CSV"),
    ("equipos:asignar", "Asignar equipos docentes"),
    ("equipos:ver", "Ver equipos docentes"),
    ("estructura:gestionar", "Gestionar carrera/materia/cohorte"),
    ("padron:importar", "Importar padrón de alumnos"),
    ("impersonacion:usar", "Usar funcionalidad de impersonación"),
    ("encuentros:gestionar", "Gestionar encuentros sincrónicos (propios)"),
    ("encuentros:ver-admin", "Ver todos los encuentros del tenant"),
    ("guardias:registrar", "Registrar guardias (propias o de cualquier docente)"),
    ("guardias:ver-admin", "Ver y exportar todas las guardias del tenant"),
    ("coloquios:gestionar", "Gestionar coloquios (crear convocatorias, importar alumnos, cerrar)"),
    ("coloquios:reservar", "Reservar turno de coloquio y cancelar reserva propia"),
    ("coloquios:ver", "Ver coloquios, métricas y agenda del tenant"),
    ("avisos:gestionar", "Gestionar avisos institucionales (crear, editar, eliminar, ver tracking)"),
    ("avisos:ver", "Ver avisos, timeline y confirmar lectura"),
    ("tareas:gestionar", "Gestionar tareas internas (crear, cambiar estado, comentar)"),
    ("auditoria:ver", "Ver auditoría de acciones del sistema"),
]

# QUÉ permisos tiene cada rol
ROLE_PERMISOS: dict[str, list[str]] = {
    "ADMIN": [p[0] for p in PERMISOS],  # Todos (incluye tareas:gestionar)
    "COORDINADOR": [
        "atrasados:ver", "equipos:ver", "equipos:asignar",
        "estructura:gestionar",
        "encuentros:gestionar", "encuentros:ver-admin",
        "guardias:registrar", "guardias:ver-admin",
        "coloquios:gestionar", "coloquios:ver",
        "avisos:gestionar", "avisos:ver",
        "tareas:gestionar", "auditoria:ver"
    ],
    "PROFESOR": [
        "atrasados:ver", "equipos:ver",
        "encuentros:gestionar", "guardias:registrar",
        "coloquios:ver",
        "avisos:ver",
        "tareas:gestionar",
    ],
    "TUTOR": [
        "atrasados:ver", "guardias:registrar",
        "avisos:ver",
    ],
    "ALUMNO": [
        "coloquios:reservar",
        "avisos:ver",
    ],
}

USERS = [
    {
        "email": "admin@trace.dev",
        "password": "Admin123456!",
        "roles": ["ADMIN", "PROFESOR"],
        "desc": "Admin principal",
    },
    {
        "email": "target@test.com",
        "password": "Target123456!",
        "roles": ["PROFESOR"],
        "desc": "Target para impersonar",
    },
    {
        "email": "admin2@test.com",
        "password": "Admin123456!",
        "roles": ["ADMIN"],
        "desc": "Segundo admin",
    },
]

ALUMNOS = [
    {
        "email": "juan@test.com",
        "password": "Test123456!",
        "nombre": "Juan",
        "apellidos": "Pérez",
        "comision": "A",
        "regional": "CABA",
    },
    {
        "email": "maria@test.com",
        "password": "Test123456!",
        "nombre": "María",
        "apellidos": "García",
        "comision": "A",
        "regional": "CABA",
    },
    {
        "email": "carlos@test.com",
        "password": "Test123456!",
        "nombre": "Carlos",
        "apellidos": "López",
        "comision": "B",
        "regional": "GBA",
    },
]

# ── Datos para seed adicional ───────────────────────────────────────────

TAREAS_SEED = [
    {
        "descripcion": "Revisar entregas TP2 de Análisis Matemático I",
        "estado": "Pendiente",
        "materia": "AM-I",
        "asignado": "target@test.com",
        "asignador": "admin@trace.dev",
    },
    {
        "descripcion": "Actualizar programa de Física I",
        "estado": "En progreso",
        "materia": "FIS-I",
        "asignado": "admin@trace.dev",
        "asignador": "admin@trace.dev",
    },
    {
        "descripcion": "Preparar material de apoyo para Programación I",
        "estado": "Resuelta",
        "materia": "PRO-I",
        "asignado": "target@test.com",
        "asignador": "admin@trace.dev",
    },
]

AVISOS_SEED = [
    {
        "titulo": "Bienvenida al ciclo lectivo 2026",
        "alcance": "Global",
        "severidad": "Info",
        "cuerpo": "Bienvenidos al ciclo lectivo 2026. Recuerden revisar el calendario académico y las fechas importantes del cuatrimestre.",
        "orden": 1,
        "requiere_ack": False,
    },
    {
        "titulo": "Recordatorio: parcial de Análisis Matemático I",
        "alcance": "PorMateria",
        "severidad": "Advertencia",
        "materia": "AM-I",
        "cuerpo": "Se recuerda a los alumnos de AM-I que el primer parcial será la próxima semana. Revisar el programa y los materiales disponibles.",
        "orden": 2,
        "requiere_ack": True,
    },
]

EVALUACIONES_SEED = [
    {
        "materia": "AM-I",
        "tipo": "Coloquio",
        "instancia": "Coloquio final AM-I - Julio 2026",
        "dias_disponibles": 3,
        "cupos_por_dia": 5,
        "dias_offset": 30,
    },
]

FECHAS_SEED = [
    {"materia": "AM-I", "tipo": "Parcial", "numero": 1, "periodo": "2026-1", "dias_offset": 14, "titulo": "1er Parcial AM-I"},
    {"materia": "AM-I", "tipo": "TP", "numero": 1, "periodo": "2026-1", "dias_offset": 21, "titulo": "Entrega TP1 AM-I"},
    {"materia": "AM-I", "tipo": "Coloquio", "numero": 1, "periodo": "2026-1", "dias_offset": 60, "titulo": "Coloquio final AM-I"},
]

PROGRAMAS_SEED = [
    {"materia": "AM-I", "titulo": "Programa de Análisis Matemático I - 2026"},
    {"materia": "FIS-I", "titulo": "Programa de Física I - 2026"},
]

SALARIOS_BASE_SEED = [
    {"rol": "PROFESOR", "monto": 150000.00},
    {"rol": "COORDINADOR", "monto": 200000.00},
    {"rol": "TUTOR", "monto": 100000.00},
    {"rol": "NEXO", "monto": 180000.00},
    {"rol": "ADMIN", "monto": 250000.00},
]

SALARIOS_PLUS_SEED = [
    {"grupo": "PROG", "rol": "PROFESOR", "monto": 25000.00, "desc": "Plus programación - profesor"},
    {"grupo": "PROG", "rol": "TUTOR", "monto": 15000.00, "desc": "Plus programación - tutor"},
    {"grupo": "BD", "rol": "PROFESOR", "monto": 25000.00, "desc": "Plus base de datos - profesor"},
    {"grupo": "MAT", "rol": "PROFESOR", "monto": 25000.00, "desc": "Plus matemática - profesor"},
    {"grupo": "ING", "rol": "PROFESOR", "monto": 20000.00, "desc": "Plus inglés - profesor"},
]


# ── Helpers ─────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(UTC)


# ── Tenant ──────────────────────────────────────────────────────────────


async def ensure_tenant_exists(session) -> None:
    """Crea el tenant de desarrollo si no existe."""
    result = await session.execute(
        text("SELECT id FROM tenant WHERE id = :tid"),
        {"tid": DEV_TENANT_ID},
    )
    if result.fetchone() is not None:
        print("  [~] Tenant de desarrollo ya existe")
        return

    await session.execute(
        text(
            "INSERT INTO tenant (id, tenant_id, nombre, created_at, updated_at) "
            "VALUES (:tid, :tid, 'Tenant Dev', now(), now())"
        ),
        {"tid": DEV_TENANT_ID},
    )
    print("  [+] Tenant de desarrollo creado")


# ── Roles ───────────────────────────────────────────────────────────────


async def ensure_roles(session) -> dict[str, UUID]:
    """Crea los roles si no existen. Devuelve {codigo: id}."""
    role_ids: dict[str, UUID] = {}

    for codigo, descripcion in ROLES:
        result = await session.execute(
            text("SELECT id FROM rol WHERE codigo = :cod AND tenant_id = :tid"),
            {"cod": codigo, "tid": DEV_TENANT_ID},
        )
        row = result.fetchone()
        if row is not None:
            role_ids[codigo] = row[0]
            print(f"  [~] Rol {codigo} ya existe")
        else:
            rid = uuid4()
            await session.execute(
                text(
                    "INSERT INTO rol (id, codigo, descripcion, tenant_id, created_at, updated_at) "
                    "VALUES (:id, :cod, :desc, :tid, now(), now())"
                ),
                {"id": rid, "cod": codigo, "desc": descripcion, "tid": DEV_TENANT_ID},
            )
            role_ids[codigo] = rid
            print(f"  [+] Rol {codigo} creado")

    return role_ids


# ── Permisos globales + asignación a roles ──────────────────────────────


async def ensure_permisos(session) -> dict[str, UUID]:
    """Crea los permisos globales si no existen. Devuelve {codigo: id}."""
    permiso_ids: dict[str, UUID] = {}

    for codigo, descripcion in PERMISOS:
        result = await session.execute(
            text("SELECT id FROM permiso WHERE codigo = :cod"),
            {"cod": codigo},
        )
        row = result.fetchone()
        if row is not None:
            permiso_ids[codigo] = row[0]
            print(f"  [~] Permiso {codigo} ya existe")
        else:
            pid = uuid4()
            await session.execute(
                text(
                    "INSERT INTO permiso (id, codigo, descripcion, created_at) "
                    "VALUES (:id, :cod, :desc, now())"
                ),
                {"id": pid, "cod": codigo, "desc": descripcion},
            )
            permiso_ids[codigo] = pid
            print(f"  [+] Permiso {codigo} creado")

    return permiso_ids


async def ensure_rol_permisos(
    session, role_ids: dict[str, UUID], permiso_ids: dict[str, UUID]
) -> None:
    """Asigna permisos a roles según ROLE_PERMISOS."""
    for rol_codigo, permisos in ROLE_PERMISOS.items():
        rid = role_ids.get(rol_codigo)
        if rid is None:
            continue
        for permiso_codigo in permisos:
            pid = permiso_ids.get(permiso_codigo)
            if pid is None:
                continue

            # Check si ya existe
            result = await session.execute(
                text(
                    "SELECT id FROM rol_permiso "
                    "WHERE tenant_id = :tid AND rol_id = :rid AND permiso_id = :pid"
                ),
                {"tid": DEV_TENANT_ID, "rid": rid, "pid": pid},
            )
            if result.fetchone() is not None:
                continue

            await session.execute(
                text(
                    "INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, created_at) "
                    "VALUES (:id, :tid, :rid, :pid, now())"
                ),
                {"id": uuid4(), "tid": DEV_TENANT_ID, "rid": rid, "pid": pid},
            )
            print(f"      Permiso {permiso_codigo} → rol {rol_codigo}")


# ── Usuarios auth ───────────────────────────────────────────────────────


async def ensure_user(
    session, email: str, password: str, role_ids: dict[str, UUID], roles: list[str]
) -> UUID:
    """Crea un usuario y le asigna roles si no existe. Devuelve su UUID."""
    repo = UserRepository(session=session, tenant_id=DEV_TENANT_ID)

    result = await session.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email},
    )
    row = result.fetchone()
    if row is not None:
        uid = row[0]
        print(f"  [~] Usuario {email} ya existe (UUID: {uid})")
        return uid

    user = await repo.create(
        email=email,
        password_hash=hash_password(password),
    )
    uid = user.id
    print(f"  [+] Usuario {email} creado (UUID: {uid})")

    for rol in roles:
        rid = role_ids.get(rol)
        if rid is None:
            print(f"      [!] Rol '{rol}' no encontrado, saltando")
            continue

        await session.execute(
            text(
                "INSERT INTO user_rol (id, user_id, rol_id, tenant_id, created_at) "
                "VALUES (:id, :uid, :rid, :tid, now()) "
                "ON CONFLICT (user_id, rol_id) DO NOTHING"
            ),
            {"id": uuid4(), "uid": uid, "rid": rid, "tid": DEV_TENANT_ID},
        )
        print(f"      Rol asignado: {rol}")

    return uid


# ── Usuario del dominio (tabla ``usuario``) ─────────────────────────────


async def ensure_usuario(
    session, auth_user_id: UUID, nombre: str, apellidos: str, email: str
) -> UUID:
    """Crea un registro en ``usuario`` ligado al auth_user si no existe."""
    result = await session.execute(
        text("SELECT id FROM usuario WHERE auth_user_id = :auid AND tenant_id = :tid"),
        {"auid": auth_user_id, "tid": DEV_TENANT_ID},
    )
    row = result.fetchone()
    if row is not None:
        return row[0]

    usuario = Usuario(
        tenant_id=DEV_TENANT_ID,
        auth_user_id=auth_user_id,
        nombre=nombre,
        apellidos=apellidos,
        email=email,
        regional="CABA",
        estado="Activo",
    )
    session.add(usuario)
    await session.flush()
    print(f"  [+] Usuario dominio {email} creado (UUID: {usuario.id})")
    return usuario.id  # type: ignore[return-value]


# ── Estructura académica ────────────────────────────────────────────────


async def ensure_carrera(session) -> UUID:
    """Crea una carrera de prueba si no existe."""
    codigo = "ING-SIS"
    result = await session.execute(
        text("SELECT id FROM carrera WHERE codigo = :cod AND tenant_id = :tid"),
        {"cod": codigo, "tid": DEV_TENANT_ID},
    )
    row = result.fetchone()
    if row is not None:
        print(f"  [~] Carrera {codigo} ya existe")
        return row[0]

    cid = uuid4()
    await session.execute(
        text(
            "INSERT INTO carrera (id, tenant_id, codigo, nombre, estado, created_at, updated_at) "
            "VALUES (:id, :tid, :cod, :nom, 'Activo', now(), now())"
        ),
        {"id": cid, "tid": DEV_TENANT_ID, "cod": codigo, "nom": "Ingeniería en Sistemas"},
    )
    print(f"  [+] Carrera {codigo} creada")
    return cid


# ── Materias del seed ─────────────────────────────────────────────────

MATERIAS_SEED: list[tuple[str, str]] = [
    ("AM-I", "Análisis Matemático I"),
    ("FIS-I", "Física I"),
    ("PRO-I", "Programación I"),
]


async def ensure_materia(session, carrera_id: UUID, codigo: str, nombre: str) -> UUID:
    """Crea una materia si no existe."""
    result = await session.execute(
        text("SELECT id FROM materia WHERE codigo = :cod AND tenant_id = :tid"),
        {"cod": codigo, "tid": DEV_TENANT_ID},
    )
    row = result.fetchone()
    if row is not None:
        print(f"  [~] Materia {codigo} ya existe")
        return row[0]

    mid = uuid4()
    await session.execute(
        text(
            "INSERT INTO materia (id, tenant_id, codigo, nombre, estado, created_at, updated_at) "
            "VALUES (:id, :tid, :cod, :nom, 'Activo', now(), now())"
        ),
        {
            "id": mid,
            "tid": DEV_TENANT_ID,
            "cod": codigo,
            "nom": nombre,
        },
    )
    print(f"  [+] Materia {codigo} — {nombre} creada")
    return mid


async def ensure_cohorte(session, carrera_id: UUID) -> UUID:
    """Crea un cohorte de prueba si no existe."""
    nombre = "2026"
    result = await session.execute(
        text(
            "SELECT id FROM cohorte "
            "WHERE nombre = :nom AND carrera_id = :cid AND tenant_id = :tid"
        ),
        {"nom": nombre, "cid": carrera_id, "tid": DEV_TENANT_ID},
    )
    row = result.fetchone()
    if row is not None:
        print(f"  [~] Cohorte {nombre} ya existe")
        return row[0]

    coid = uuid4()
    await session.execute(
        text(
            "INSERT INTO cohorte (id, tenant_id, carrera_id, nombre, anio, vig_desde, estado, created_at, updated_at) "
            "VALUES (:id, :tid, :cid, :nom, :anio, now()::date, 'Activo', now(), now())"
        ),
        {
            "id": coid,
            "tid": DEV_TENANT_ID,
            "cid": carrera_id,
            "nom": nombre,
            "anio": 2026,
        },
    )
    print(f"  [+] Cohorte {nombre} creado")
    return coid


# ── Asignación (profesor) + Umbral ──────────────────────────────────────


async def ensure_asignacion_profesor(
    session, materia_id: UUID, usuario_id: UUID
) -> UUID:
    """Asigna un profesor a una materia si no existe."""
    result = await session.execute(
        text(
            "SELECT id FROM asignacion "
            "WHERE usuario_id = :uid AND materia_id = :mid "
            "AND tenant_id = :tid AND deleted_at IS NULL"
        ),
        {"uid": usuario_id, "mid": materia_id, "tid": DEV_TENANT_ID},
    )
    row = result.fetchone()
    if row is not None:
        print(f"  [~] Asignación profesor -> materia ya existe")
        return row[0]

    aid = uuid4()
    await session.execute(
        text(
            "INSERT INTO asignacion "
            "(id, tenant_id, usuario_id, rol, materia_id, desde, created_at, updated_at) "
            "VALUES (:id, :tid, :uid, 'PROFESOR', :mid, now(), now(), now())"
        ),
        {"id": aid, "tid": DEV_TENANT_ID, "uid": usuario_id, "mid": materia_id},
    )
    print(f"  [+] Asignación profesor -> materia creada")
    return aid


async def ensure_umbral(
    session, asignacion_id: UUID, materia_id: UUID
) -> None:
    """Crea umbral de aprobación si no existe (por materia + asignacion)."""
    result = await session.execute(
        text(
            "SELECT id FROM umbral_materia "
            "WHERE materia_id = :mid AND asignacion_id = :aid "
            "AND tenant_id = :tid AND deleted_at IS NULL"
        ),
        {"mid": materia_id, "aid": asignacion_id, "tid": DEV_TENANT_ID},
    )
    if result.fetchone() is not None:
        print("  [~] Umbral de materia ya existe")
        return

    uid = uuid4()
    await session.execute(
        text(
            "INSERT INTO umbral_materia "
            "(id, tenant_id, asignacion_id, materia_id, umbral_pct, created_at, updated_at) "
            "VALUES (:id, :tid, :aid, :mid, 60, now(), now())"
        ),
        {
            "id": uid,
            "tid": DEV_TENANT_ID,
            "aid": asignacion_id,
            "mid": materia_id,
        },
    )
    print("  [+] Umbral de materia creado (60%)")


# ── Alumnos ─────────────────────────────────────────────────────────────


async def ensure_alumno_user(
    session,
    alumno: dict,
    role_ids: dict[str, UUID],
) -> tuple[UUID, UUID]:
    """Crea auth_user + usuario dominio para un alumno.
    
    Returns:
        (auth_user_id, usuario_id)
    """
    # 1. Crear auth user
    auth_uid = await ensure_user(
        session,
        email=alumno["email"],
        password=alumno["password"],
        role_ids=role_ids,
        roles=["ALUMNO"],
    )

    # 2. Crear usuario dominio
    usuario_id = await ensure_usuario(
        session,
        auth_user_id=auth_uid,
        nombre=alumno["nombre"],
        apellidos=alumno["apellidos"],
        email=alumno["email"],
    )

    return auth_uid, usuario_id


# ── Versión padron + Entradas ───────────────────────────────────────────


async def ensure_version_padron(
    session, materia_id: UUID, cohorte_id: UUID, cargado_por: UUID
) -> UUID:
    """Crea una version de padrón activa si no existe."""
    result = await session.execute(
        text(
            "SELECT id FROM version_padron "
            "WHERE materia_id = :mid AND cohorte_id = :coid "
            "AND tenant_id = :tid AND activa = true AND deleted_at IS NULL"
        ),
        {"mid": materia_id, "coid": cohorte_id, "tid": DEV_TENANT_ID},
    )
    row = result.fetchone()
    if row is not None:
        print(f"  [~] VersionPadron ya existe")
        return row[0]

    vid = uuid4()
    await session.execute(
        text(
            "INSERT INTO version_padron "
            "(id, tenant_id, materia_id, cohorte_id, cargado_por, activa, created_at, updated_at) "
            "VALUES (:id, :tid, :mid, :coid, :cp, true, now(), now())"
        ),
        {
            "id": vid,
            "tid": DEV_TENANT_ID,
            "mid": materia_id,
            "coid": cohorte_id,
            "cp": cargado_por,
        },
    )
    print(f"  [+] VersionPadron creada")
    return vid


async def ensure_entrada_padron(
    session,
    version_id: UUID,
    usuario_id: UUID,
    nombre: str,
    apellidos: str,
    email: str,
    comision: str = "A",
    regional: str = "CABA",
) -> UUID:
    """Crea una entrada de padrón si no existe."""
    # Usamos ORM para que el EncryptedColumn funcione automáticamente
    result = await session.execute(
        text(
            "SELECT id FROM entrada_padron "
            "WHERE version_id = :vid AND usuario_id = :uid "
            "AND tenant_id = :tid AND deleted_at IS NULL"
        ),
        {"vid": version_id, "uid": usuario_id, "tid": DEV_TENANT_ID},
    )
    row = result.fetchone()
    if row is not None:
        return row[0]

    entrada = EntradaPadron(
        tenant_id=DEV_TENANT_ID,
        version_id=version_id,
        usuario_id=usuario_id,
        nombre=nombre,
        apellidos=apellidos,
        email=email,
        comision=comision,
        regional=regional,
    )
    session.add(entrada)
    await session.flush()
    print(f"  [+] EntradaPadron {email} creada")
    return entrada.id  # type: ignore[return-value]


# ── Calificaciones ──────────────────────────────────────────────────────


async def ensure_calificaciones(
    session,
    materia_id: UUID,
    entradas: list[dict],  # [{entrada_id, usuario_id, nombre, apellidos}]
) -> None:
    """Crea calificaciones de prueba para cada entrada de padrón.
    
    Crea 2 actividades por alumno con distintas notas para probar
    atrasados/ranking/reportes.
    """
    actividades_notas = [
        # (actividad, nota, aprobado)
        ("TP1", 8.0, True),
        ("TP2", 6.0, True),
        ("TP3", 4.0, False),
    ]

    total = 0
    for entrada in entradas:
        eid = entrada["entrada_id"]
        for actividad, nota, aprobado in actividades_notas:
            # Check si ya existe
            result = await session.execute(
                text(
                    "SELECT id FROM calificacion "
                    "WHERE entrada_padron_id = :eid AND materia_id = :mid "
                    "AND actividad = :act AND tenant_id = :tid AND deleted_at IS NULL"
                ),
                {
                    "eid": eid,
                    "mid": materia_id,
                    "act": actividad,
                    "tid": DEV_TENANT_ID,
                },
            )
            if result.fetchone() is not None:
                continue

            calif = Calificacion(
                tenant_id=DEV_TENANT_ID,
                entrada_padron_id=eid,
                materia_id=materia_id,
                actividad=actividad,
                nota_numerica=nota,
                aprobado=aprobado,
                origen="IMPORTADO",
            )
            session.add(calif)
            total += 1

    if total > 0:
        await session.flush()
        print(f"  [+] {total} calificaciones creadas")
    else:
        print("  [~] Calificaciones ya existen")


# ── Encuentros ────────────────────────────────────────────────────────────


async def ensure_slot_recurrente(
    session, materia_id: UUID, asignacion_id: UUID | None = None
) -> UUID:
    """Crea un slot recurrente de ejemplo si no existe."""
    titulo = "Clase de Análisis Matemático I"
    result = await session.execute(
        text("SELECT id FROM slot_encuentro WHERE titulo = :tit AND materia_id = :mid AND tenant_id = :tid"),
        {"tit": titulo, "mid": materia_id, "tid": DEV_TENANT_ID},
    )
    row = result.fetchone()
    if row is not None:
        print(f"  [~] Slot recurrente ya existe")
        return row[0]

    sid = uuid4()
    from datetime import date, time

    await session.execute(
        text("""
            INSERT INTO slot_encuentro
                (id, tenant_id, asignacion_id, materia_id, titulo, hora,
                 dia_semana, fecha_inicio, cant_semanas, meet_url,
                 created_at, updated_at)
            VALUES
                (:id, :tid, :aid, :mid, :tit, :hora,
                 :dia, :fecha_ini, :semanas, :meet,
                 now(), now())
        """),
        {
            "id": sid,
            "tid": DEV_TENANT_ID,
            "aid": asignacion_id,
            "mid": materia_id,
            "tit": titulo,
            "hora": time(18, 0),
            "dia": "Lunes",
            "fecha_ini": date(2026, 6, 8),
            "semanas": 4,
            "meet": "https://meet.google.com/abc-defg-hij",
        },
    )
    print(f"  [+] Slot recurrente '{titulo}' creado")
    return sid


async def ensure_instancias(session, slot_id: UUID, materia_id: UUID) -> None:
    """Crea instancias de ejemplo para un slot si no existen."""
    from datetime import date, time, timedelta

    # Check if instances already exist for this slot
    result = await session.execute(
        text("SELECT COUNT(*) FROM instancia_encuentro WHERE slot_id = :sid AND tenant_id = :tid"),
        {"sid": slot_id, "tid": DEV_TENANT_ID},
    )
    if result.scalar() > 0:
        print(f"  [~] Instancias del slot ya existen")
        return

    base_fecha = date(2026, 6, 8)
    created = 0
    for i in range(4):
        iid = uuid4()
        await session.execute(
            text("""
                INSERT INTO instancia_encuentro
                    (id, tenant_id, slot_id, materia_id, fecha, hora,
                     titulo, estado, meet_url, created_at, updated_at)
                VALUES
                    (:id, :tid, :sid, :mid, :fecha, :hora,
                     :tit, :est, :meet, now(), now())
            """),
            {
                "id": iid,
                "tid": DEV_TENANT_ID,
                "sid": slot_id,
                "mid": materia_id,
                "fecha": base_fecha + timedelta(weeks=i),
                "hora": time(18, 0),
                "tit": "Clase de Análisis Matemático I",
                "est": "Programado",
                "meet": "https://meet.google.com/abc-defg-hij",
            },
        )
        created += 1

    print(f"  [+] {created} instancias de encuentro creadas")


# ── Guardias ──────────────────────────────────────────────────────────────


async def ensure_guardia(
    session, materia_id: UUID, carrera_id: UUID, cohorte_id: UUID,
    asignacion_id: UUID | None = None,
) -> None:
    """Crea una guardia de ejemplo si no existe."""
    result = await session.execute(
        text("""SELECT id FROM guardia
                WHERE materia_id = :mid AND tenant_id = :tid
                  AND horario = :hor AND deleted_at IS NULL"""),
        {"mid": materia_id, "tid": DEV_TENANT_ID, "hor": "14:00–14:45"},
    )
    if result.fetchone() is not None:
        print(f"  [~] Guardia de ejemplo ya existe")
        return

    gid = uuid4()
    await session.execute(
        text("""
            INSERT INTO guardia
                (id, tenant_id, asignacion_id, materia_id, carrera_id, cohorte_id,
                 dia, horario, estado, comentarios, creada_at, created_at, updated_at)
            VALUES
                (:id, :tid, :aid, :mid, :cid, :coid,
                 :dia, :hor, :est, :com, now(), now(), now())
        """),
        {
            "id": gid,
            "tid": DEV_TENANT_ID,
            "aid": asignacion_id,
            "mid": materia_id,
            "cid": carrera_id,
            "coid": cohorte_id,
            "dia": "Martes",
            "hor": "14:00–14:45",
            "est": "Pendiente",
            "com": "Consulta general - Atención a alumnos",
        },
    )
    print(f"  [+] Guardia de ejemplo creada")


# ── Tareas ────────────────────────────────────────────────────────────────


async def ensure_tareas(
    session, materia_ids: dict[str, UUID], usuario_ids: dict[str, UUID]
) -> None:
    """Crea tareas de ejemplo si no existen."""
    from datetime import datetime, timezone

    for td in TAREAS_SEED:
        mid = materia_ids.get(td["materia"])
        asignado_uid = usuario_ids.get(td["asignado"])
        asignador_uid = usuario_ids.get(td["asignador"])
        if not mid or not asignado_uid or not asignador_uid:
            print(f"  [!] Tarea '{td['descripcion']}' — faltan referencias, saltando")
            continue

        result = await session.execute(
            text("SELECT id FROM tarea WHERE descripcion = :desc AND tenant_id = :tid"),
            {"desc": td["descripcion"], "tid": DEV_TENANT_ID},
        )
        if result.fetchone() is not None:
            print(f"  [~] Tarea '{td['descripcion'][:40]}...' ya existe")
            continue

        tid = uuid4()
        await session.execute(
            text("""
                INSERT INTO tarea
                    (id, tenant_id, materia_id, asignado_a, asignado_por,
                     estado, descripcion, created_at, updated_at)
                VALUES
                    (:id, :tid, :mid, :asig_a, :asig_por,
                     :est, :desc, now(), now())
            """),
            {
                "id": tid,
                "tid": DEV_TENANT_ID,
                "mid": mid,
                "asig_a": asignado_uid,
                "asig_por": asignador_uid,
                "est": td["estado"],
                "desc": td["descripcion"],
            },
        )
        print(f"  [+] Tarea '{td['descripcion'][:40]}...' creada")


# ── Avisos ────────────────────────────────────────────────────────────────


async def ensure_avisos(
    session, materia_ids: dict[str, UUID], cohorte_id: UUID
) -> None:
    """Crea avisos de ejemplo si no existen."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)

    for av in AVISOS_SEED:
        # Checkear unicidad por titulo
        result = await session.execute(
            text("SELECT id FROM aviso WHERE titulo = :tit AND tenant_id = :tid"),
            {"tit": av["titulo"], "tid": DEV_TENANT_ID},
        )
        if result.fetchone() is not None:
            print(f"  [~] Aviso '{av['titulo']}' ya existe")
            continue

        mid = materia_ids.get(av.get("materia", "")) if av.get("materia") else None

        aviso = Aviso(
            tenant_id=DEV_TENANT_ID,
            alcance=av["alcance"],
            materia_id=mid,
            cohorte_id=cohorte_id if av["alcance"] in ("PorMateria", "PorCohorte") else None,
            severidad=av["severidad"],
            titulo=av["titulo"],
            cuerpo=av["cuerpo"],
            inicio_en=now,
            fin_en=now + timedelta(days=30),
            orden=av["orden"],
            activo=True,
            requiere_ack=av["requiere_ack"],
        )
        session.add(aviso)
        await session.flush()
        print(f"  [+] Aviso '{av['titulo']}' creado")


# ── Evaluaciones ──────────────────────────────────────────────────────────


async def ensure_evaluaciones(
    session, materia_ids: dict[str, UUID], cohorte_id: UUID
) -> None:
    """Crea evaluaciones de ejemplo si no existen."""
    from datetime import date, timedelta

    today = date.today()

    for ev in EVALUACIONES_SEED:
        mid = materia_ids.get(ev["materia"])
        if not mid:
            continue

        result = await session.execute(
            text("""SELECT id FROM evaluacion
                    WHERE materia_id = :mid AND cohorte_id = :coid
                      AND tipo = :tipo AND tenant_id = :tid"""),
            {"mid": mid, "coid": cohorte_id, "tipo": ev["tipo"], "tid": DEV_TENANT_ID},
        )
        if result.fetchone() is not None:
            print(f"  [~] Evaluación '{ev['instancia']}' ya existe")
            continue

        eid = uuid4()
        await session.execute(
            text("""
                INSERT INTO evaluacion
                    (id, tenant_id, materia_id, cohorte_id, tipo, instancia,
                     dias_disponibles, cupos_por_dia, fecha_inicio, fecha_fin, estado,
                     created_at, updated_at)
                VALUES
                    (:id, :tid, :mid, :coid, :tipo, :inst,
                     :dias, :cupos, :f_ini, :f_fin, 'Activa',
                     now(), now())
            """),
            {
                "id": eid,
                "tid": DEV_TENANT_ID,
                "mid": mid,
                "coid": cohorte_id,
                "tipo": ev["tipo"],
                "inst": ev["instancia"],
                "dias": ev["dias_disponibles"],
                "cupos": ev["cupos_por_dia"],
                "f_ini": today,
                "f_fin": today + timedelta(days=ev["dias_offset"]),
            },
        )
        print(f"  [+] Evaluación '{ev['instancia']}' creada")


# ── Fechas académicas ─────────────────────────────────────────────────────


async def ensure_fechas_academicas(
    session, materia_ids: dict[str, UUID], cohorte_id: UUID
) -> None:
    """Crea fechas académicas de ejemplo si no existen."""
    from datetime import date, timedelta

    today = date.today()

    for fd in FECHAS_SEED:
        mid = materia_ids.get(fd["materia"])
        if not mid:
            continue

        result = await session.execute(
            text("""SELECT id FROM fecha_academica
                    WHERE materia_id = :mid AND cohorte_id = :coid
                      AND tipo = :tipo AND numero = :num AND tenant_id = :tid"""),
            {"mid": mid, "coid": cohorte_id, "tipo": fd["tipo"], "num": fd["numero"], "tid": DEV_TENANT_ID},
        )
        if result.fetchone() is not None:
            print(f"  [~] Fecha académica '{fd['titulo']}' ya existe")
            continue

        faid = uuid4()
        await session.execute(
            text("""
                INSERT INTO fecha_academica
                    (id, tenant_id, materia_id, cohorte_id, tipo, numero,
                     periodo, fecha, titulo, created_at, updated_at)
                VALUES
                    (:id, :tid, :mid, :coid, :tipo, :num,
                     :per, :fecha, :tit, now(), now())
            """),
            {
                "id": faid,
                "tid": DEV_TENANT_ID,
                "mid": mid,
                "coid": cohorte_id,
                "tipo": fd["tipo"],
                "num": fd["numero"],
                "per": fd["periodo"],
                "fecha": today + timedelta(days=fd["dias_offset"]),
                "tit": fd["titulo"],
            },
        )
        print(f"  [+] Fecha académica '{fd['titulo']}' creada")


# ── Programas de materia ──────────────────────────────────────────────────


async def ensure_programas(
    session, materia_ids: dict[str, UUID], carrera_id: UUID, cohorte_id: UUID
) -> None:
    """Crea programas de materia de ejemplo si no existen."""
    from datetime import datetime, timezone

    for prog in PROGRAMAS_SEED:
        mid = materia_ids.get(prog["materia"])
        if not mid:
            continue

        result = await session.execute(
            text("""SELECT id FROM programa_materia
                    WHERE materia_id = :mid AND carrera_id = :cid
                      AND cohorte_id = :coid AND tenant_id = :tid"""),
            {"mid": mid, "cid": carrera_id, "coid": cohorte_id, "tid": DEV_TENANT_ID},
        )
        if result.fetchone() is not None:
            print(f"  [~] Programa '{prog['titulo']}' ya existe")
            continue

        pid = uuid4()
        await session.execute(
            text("""
                INSERT INTO programa_materia
                    (id, tenant_id, materia_id, carrera_id, cohorte_id,
                     titulo, referencia_archivo, cargado_at, created_at, updated_at)
                VALUES
                    (:id, :tid, :mid, :cid, :coid,
                     :tit, :ref, now(), now(), now())
            """),
            {
                "id": pid,
                "tid": DEV_TENANT_ID,
                "mid": mid,
                "cid": carrera_id,
                "coid": cohorte_id,
                "tit": prog["titulo"],
                "ref": uuid4(),
            },
        )
        print(f"  [+] Programa '{prog['titulo']}' creado")


# ── Comunicaciones ────────────────────────────────────────────────────────


async def ensure_comunicaciones(
    session, materia_ids: dict[str, UUID], usuario_ids: dict[str, UUID],
    encryption_key: str,
) -> None:
    """Crea comunicaciones de ejemplo si no existen."""
    from datetime import datetime, timezone

    admin_uid = usuario_ids.get("admin@trace.dev")
    juan_uid = usuario_ids.get("juan@test.com")
    if not admin_uid or not juan_uid:
        print("  [!] Faltan usuarios para comunicaciones, saltando")
        return

    result = await session.execute(
        text("SELECT id FROM comunicaciones WHERE asunto = :asunto AND tenant_id = :tid"),
        {"asunto": "Bienvenida al sistema trace", "tid": DEV_TENANT_ID},
    )
    if result.fetchone() is not None:
        print("  [~] Comunicación de bienvenida ya existe")
        return

    # Encriptamos el destinatario manualmente (raw SQL evita el ORM Enum)
    crypto = EncryptionService(encryption_key)
    destinatario_enc = crypto.encrypt("juan@test.com")

    cid = uuid4()
    await session.execute(
        text("""
            INSERT INTO comunicaciones
                (id, tenant_id, enviado_por_id, materia_id, destinatario,
                 asunto, cuerpo, estado, lote_id, created_at, updated_at)
            VALUES
                (:id, :tid, :ep, :mid, :dest,
                 :asunto, :cuerpo, 'Pendiente', :lote, now(), now())
        """),
        {
            "id": cid,
            "tid": DEV_TENANT_ID,
            "ep": admin_uid,
            "mid": materia_ids.get("AM-I"),
            "dest": destinatario_enc,
            "asunto": "Bienvenida al sistema trace",
            "cuerpo": "Te damos la bienvenida al sistema de gestión académica trace. "
                      "Recordá que podés consultar tus calificaciones, "
                      "reservar turnos de coloquio y recibir avisos institucionales.",
            "lote": uuid4(),
        },
    )
    print("  [+] Comunicación de bienvenida creada")


# ── Mensajería ────────────────────────────────────────────────────────────


async def ensure_mensajeria(
    session, usuario_ids: dict[str, UUID]
) -> None:
    """Crea un hilo de mensajería de ejemplo si no existen."""
    from datetime import datetime, timezone

    admin_uid = usuario_ids.get("admin@trace.dev")
    target_uid = usuario_ids.get("target@test.com")
    if not admin_uid or not target_uid:
        print("  [!] Faltan usuarios para mensajería, saltando")
        return

    result = await session.execute(
        text("SELECT id FROM mensaje_hilo WHERE asunto = :asunto AND tenant_id = :tid"),
        {"asunto": "Consulta sobre programación de AM-I", "tid": DEV_TENANT_ID},
    )
    if result.fetchone() is not None:
        print("  [~] Hilo de mensajería ya existe")
        return

    hilo_id = uuid4()
    await session.execute(
        text("""
            INSERT INTO mensaje_hilo
                (id, tenant_id, asunto, usuario_a_id, usuario_b_id, created_at, updated_at)
            VALUES
                (:id, :tid, :asunto, :ua, :ub, now(), now())
        """),
        {
            "id": hilo_id,
            "tid": DEV_TENANT_ID,
            "asunto": "Consulta sobre programación de AM-I",
            "ua": admin_uid,
            "ub": target_uid,
        },
    )
    print("  [+] Hilo de mensajería creado")

    # Mensaje 1: admin -> target
    msg1_id = uuid4()
    await session.execute(
        text("""
            INSERT INTO mensaje
                (id, tenant_id, hilo_id, autor_id, cuerpo, creado_at)
            VALUES
                (:id, :tid, :hilo, :autor, :cuerpo, now())
        """),
        {
            "id": msg1_id,
            "tid": DEV_TENANT_ID,
            "hilo": hilo_id,
            "autor": admin_uid,
            "cuerpo": "Hola, ¿podrías revisar la programación de las clases de AM-I para la próxima semana? Necesito confirmar los horarios.",
        },
    )
    print("  [+] Mensaje 1 del hilo creado")

    # Mensaje 2: target -> admin
    msg2_id = uuid4()
    await session.execute(
        text("""
            INSERT INTO mensaje
                (id, tenant_id, hilo_id, autor_id, cuerpo, creado_at)
            VALUES
                (:id, :tid, :hilo, :autor, :cuerpo, now() + interval '1 hour')
        """),
        {
            "id": msg2_id,
            "tid": DEV_TENANT_ID,
            "hilo": hilo_id,
            "autor": target_uid,
            "cuerpo": "Hola, sí. Las clases de AM-I están programadas los lunes de 18 a 20hs. Ya subí el cronograma actualizado al sistema.",
        },
    )
    print("  [+] Mensaje 2 del hilo creado")


# ── Salarios y Liquidaciones ──────────────────────────────────────────────


async def ensure_salarios(session) -> None:
    """Crea los salarios base y plus de ejemplo si no existen."""
    # Salarios base
    for sb in SALARIOS_BASE_SEED:
        result = await session.execute(
            text("""SELECT id FROM salario_base
                    WHERE rol = :rol AND tenant_id = :tid
                      AND hasta IS NULL"""),
            {"rol": sb["rol"], "tid": DEV_TENANT_ID},
        )
        if result.fetchone() is not None:
            print(f"  [~] Salario base para {sb['rol']} ya existe")
            continue

        sbid = uuid4()
        await session.execute(
            text("""
                INSERT INTO salario_base
                    (id, tenant_id, rol, monto, desde, created_at, updated_at)
                VALUES
                    (:id, :tid, :rol, :monto, now()::date, now(), now())
            """),
            {"id": sbid, "tid": DEV_TENANT_ID, "rol": sb["rol"], "monto": sb["monto"]},
        )
        print(f"  [+] Salario base para {sb['rol']}: ${sb['monto']:,.0f}")

    # Salarios plus
    for sp in SALARIOS_PLUS_SEED:
        result = await session.execute(
            text("""SELECT id FROM salario_plus
                    WHERE grupo = :grupo AND rol = :rol AND tenant_id = :tid
                      AND hasta IS NULL"""),
            {"grupo": sp["grupo"], "rol": sp["rol"], "tid": DEV_TENANT_ID},
        )
        if result.fetchone() is not None:
            print(f"  [~] Salario plus grupo={sp['grupo']} rol={sp['rol']} ya existe")
            continue

        spid = uuid4()
        await session.execute(
            text("""
                INSERT INTO salario_plus
                    (id, tenant_id, grupo, rol, descripcion, monto, desde, created_at, updated_at)
                VALUES
                    (:id, :tid, :grupo, :rol, :desc, :monto, now()::date, now(), now())
            """),
            {
                "id": spid,
                "tid": DEV_TENANT_ID,
                "grupo": sp["grupo"],
                "rol": sp["rol"],
                "desc": sp.get("desc", ""),
                "monto": sp["monto"],
            },
        )
        print(f"  [+] Salario plus grupo={sp['grupo']} rol={sp['rol']}: ${sp['monto']:,.0f}")


async def ensure_liquidacion(
    session, cohorte_id: UUID, usuario_ids: dict[str, UUID]
) -> None:
    """Crea una liquidación de ejemplo si no existe."""
    admin_uid = usuario_ids.get("admin@trace.dev")
    if not admin_uid:
        print("  [!] No se encontró admin para liquidación, saltando")
        return

    result = await session.execute(
        text("""SELECT id FROM liquidacion
                WHERE periodo = '2026-06' AND usuario_id = :uid
                  AND tenant_id = :tid AND deleted_at IS NULL"""),
        {"uid": admin_uid, "tid": DEV_TENANT_ID},
    )
    if result.fetchone() is not None:
        print("  [~] Liquidación de ejemplo ya existe")
        return

    lid = uuid4()
    await session.execute(
        text("""
            INSERT INTO liquidacion
                (id, tenant_id, cohorte_id, periodo, usuario_id, rol,
                 comisiones, monto_base, monto_plus, total,
                 es_nexo, excluido_por_factura, estado,
                 created_at, updated_at)
            VALUES
                (:id, :tid, :coid, '2026-06', :uid, 'PROFESOR',
                 '["A", "B"]', 150000, 0, 150000,
                 false, false, 'Abierta',
                 now(), now())
        """),
        {"id": lid, "tid": DEV_TENANT_ID, "coid": cohorte_id, "uid": admin_uid},
    )
    print("  [+] Liquidación de ejemplo creada (admin@trace.dev, periodo 2026-06, $150.000)")


# ── Main ────────────────────────────────────────────────────────────────


async def main() -> None:
    settings = Settings()
    db_display = (
        settings.DATABASE_URL.split("@")[1]
        if "@" in settings.DATABASE_URL
        else settings.DATABASE_URL
    )
    print(f"\nConectando a {db_display}...\n")

    await close_engine()
    init_engine(settings.DATABASE_URL, encryption_key=settings.ENCRYPTION_KEY)
    maker = get_session_maker()

    async with maker() as session:
        # ── 1. Tenant ────────────────────────────────────────────────
        await ensure_tenant_exists(session)

        # ── 2. Roles ─────────────────────────────────────────────────
        role_ids = await ensure_roles(session)

        # ── 3. Permisos globales (+ asignación a roles) ──────────────
        print()
        permiso_ids = await ensure_permisos(session)
        await ensure_rol_permisos(session, role_ids, permiso_ids)

        # ── 4. Usuarios existentes ───────────────────────────────────
        print()
        main_user_ids: dict[str, UUID] = {}  # email -> users.id
        for user_cfg in USERS:
            uid = await ensure_user(
                session,
                email=user_cfg["email"],
                password=user_cfg["password"],
                role_ids=role_ids,
                roles=user_cfg["roles"],
            )
            main_user_ids[user_cfg["email"]] = uid

            # También crear registro en tabla `usuario` (FK desde asignacion, etc.)
            # Usamos el email como nombre/apellidos simplificado si no hay más datos
            name_parts = user_cfg["email"].split("@")[0].split(".")
            nombre = name_parts[0].capitalize() if name_parts else user_cfg["email"]
            apellidos = name_parts[1].capitalize() if len(name_parts) > 1 else "."
            await ensure_usuario(session, uid, nombre, apellidos, user_cfg["email"])

        # ── 5. Estructura académica ──────────────────────────────────
        print()
        carrera_id = await ensure_carrera(session)
        cohorte_id = await ensure_cohorte(session, carrera_id)

        # Crear todas las materias
        materia_ids: dict[str, UUID] = {}
        for codigo, nombre in MATERIAS_SEED:
            mid = await ensure_materia(session, carrera_id, codigo, nombre)
            materia_ids[codigo] = mid

        # Obtener UUID de la tabla `usuario` para todos los usuarios
        usuario_ids: dict[str, UUID] = {}  # email -> usuario.id
        for email in ("admin@trace.dev", "target@test.com", "admin2@test.com"):
            row = (
                await session.execute(
                    text("SELECT id FROM usuario WHERE auth_user_id = :auid"),
                    {"auid": main_user_ids.get(email)},
                )
            ).fetchone()
            if row:
                usuario_ids[email] = row[0]

        target_usuario_row = (
            await session.execute(
                text("SELECT id FROM usuario WHERE auth_user_id = :auid"),
                {"auid": main_user_ids.get("target@test.com")},
            )
        ).fetchone()

        admin_usuario_row = (
            await session.execute(
                text("SELECT id FROM usuario WHERE auth_user_id = :auid"),
                {"auid": main_user_ids.get("admin@trace.dev")},
            )
        ).fetchone()

        # ── 6. Asignaciones profesor + umbrales ──────────────────────
        print()
        target_asignacion_id: UUID | None = None
        admin_asignaciones: dict[str, UUID] = {}  # materia_codigo -> asignacion_id

        # target@test.com → AM-I (mantener compatibilidad)
        if target_usuario_row:
            target_asignacion_id = await ensure_asignacion_profesor(
                session, materia_ids["AM-I"], target_usuario_row[0]
            )
            await ensure_umbral(session, target_asignacion_id, materia_ids["AM-I"])
        else:
            print("  [!] No se encontró target@test.com, saltando asignación")

        # admin@trace.dev → todas las materias
        if admin_usuario_row:
            for codigo in ("AM-I", "FIS-I", "PRO-I"):
                aid = await ensure_asignacion_profesor(
                    session, materia_ids[codigo], admin_usuario_row[0]
                )
                admin_asignaciones[codigo] = aid
                await ensure_umbral(session, aid, materia_ids[codigo])
        else:
            print("  [!] No se encontró admin@trace.dev, saltando asignaciones admin")

        # ── 7. Alumnos ───────────────────────────────────────────────
        print()
        alumno_usuarios: list[dict] = []
        for alumno in ALUMNOS:
            auth_uid, usuario_id = await ensure_alumno_user(session, alumno, role_ids)
            usuario_ids[alumno["email"]] = usuario_id
            alumno_usuarios.append({
                "auth_uid": auth_uid,
                "usuario_id": usuario_id,
                "nombre": alumno["nombre"],
                "apellidos": alumno["apellidos"],
                "email": alumno["email"],
                "comision": alumno["comision"],
                "regional": alumno["regional"],
            })

        # ── 8. Versión padron + entradas (por cada materia) ──────────
        print()
        cargado_por_id = (
            target_usuario_row[0]
            if target_usuario_row
            else admin_usuario_row[0] if admin_usuario_row else None
        )

        entradas_por_materia: dict[str, list[dict]] = {}

        for codigo in ("AM-I", "FIS-I", "PRO-I"):
            mid = materia_ids[codigo]
            if cargado_por_id is None:
                admin_result = await session.execute(
                    text("SELECT id FROM users WHERE email = 'admin@trace.dev'"),
                )
                admin_row = admin_result.fetchone()
                version_id = await ensure_version_padron(
                    session, mid, cohorte_id, admin_row[0]
                )
            else:
                version_id = await ensure_version_padron(
                    session, mid, cohorte_id, cargado_por_id
                )

            entradas_materia: list[dict] = []
            for au in alumno_usuarios:
                eid = await ensure_entrada_padron(
                    session,
                    version_id=version_id,
                    usuario_id=au["usuario_id"],
                    nombre=au["nombre"],
                    apellidos=au["apellidos"],
                    email=au["email"],
                    comision=au["comision"],
                    regional=au["regional"],
                )
                entradas_materia.append({
                    "entrada_id": eid,
                    "usuario_id": au["usuario_id"],
                    "nombre": au["nombre"],
                    "apellidos": au["apellidos"],
                })

            entradas_por_materia[codigo] = entradas_materia

        # ── 9. Calificaciones (por cada materia) ─────────────────────
        print()
        for codigo in ("AM-I", "FIS-I", "PRO-I"):
            await ensure_calificaciones(
                session, materia_ids[codigo], entradas_por_materia[codigo]
            )

        # ── 10. Encuentros (solo para AM-I, materia de referencia) ─────
        print()
        slot_id = await ensure_slot_recurrente(
            session, materia_ids["AM-I"],
            asignacion_id=target_asignacion_id if target_usuario_row else None,
        )
        await ensure_instancias(session, slot_id, materia_ids["AM-I"])

        # ── 11. Guardias (solo para AM-I) ────────────────────────────
        print()
        await ensure_guardia(
            session, materia_ids["AM-I"], carrera_id, cohorte_id,
            asignacion_id=target_asignacion_id if target_usuario_row else None,
        )

        # ── 12. Tareas ──────────────────────────────────────────────
        print()
        await ensure_tareas(session, materia_ids, usuario_ids)

        # ── 13. Avisos ──────────────────────────────────────────────
        print()
        await ensure_avisos(session, materia_ids, cohorte_id)

        # ── 14. Evaluaciones ────────────────────────────────────────
        print()
        await ensure_evaluaciones(session, materia_ids, cohorte_id)

        # ── 15. Fechas académicas ───────────────────────────────────
        print()
        await ensure_fechas_academicas(session, materia_ids, cohorte_id)

        # ── 16. Programas de materia ────────────────────────────────
        print()
        await ensure_programas(session, materia_ids, carrera_id, cohorte_id)

        # ── 17. Comunicaciones ──────────────────────────────────────
        print()
        await ensure_comunicaciones(session, materia_ids, usuario_ids, settings.ENCRYPTION_KEY)

        # ── 18. Mensajería ─────────────────────────────────────────
        print()
        await ensure_mensajeria(session, usuario_ids)

        # ── 19. Salarios y Liquidaciones ────────────────────────────
        print()
        await ensure_salarios(session)
        await ensure_liquidacion(session, cohorte_id, usuario_ids)

        # ── Commit ───────────────────────────────────────────────────
        await session.commit()

    await close_engine()

    total_usuarios = len(USERS) + len(ALUMNOS)
    total_entradas = sum(len(e) for e in entradas_por_materia.values())
    print(f"\n[OK] Seed completado.")
    print(f"  • {total_usuarios} usuarios creados")
    print(f"  • {len(PERMISOS)} permisos + asignación a roles")
    print(f"  • 1 carrera, {len(MATERIAS_SEED)} materias, 1 cohorte")
    print(f"  • {total_entradas} entradas de padrón ({len(MATERIAS_SEED)} materias)")
    print(f"  • Calificaciones de prueba en {len(MATERIAS_SEED)} materias")
    print(f"  • admin@trace.dev asignado a las {len(MATERIAS_SEED)} materias (PROFESOR)")
    print(f"  • Slot recurrente + 4 instancias de encuentro")
    print(f"  • 1 guardia de ejemplo")
    print(f"  • {len(TAREAS_SEED)} tareas internas")
    print(f"  • {len(AVISOS_SEED)} avisos")
    print(f"  • {len(EVALUACIONES_SEED)} evaluación (coloquio)")
    print(f"  • {len(FECHAS_SEED)} fechas académicas")
    print(f"  • {len(PROGRAMAS_SEED)} programas de materia")
    print(f"  • 1 comunicación")
    print(f"  • 1 hilo de mensajería (2 mensajes)")
    print(f"  • {len(SALARIOS_BASE_SEED)} salarios base + {len(SALARIOS_PLUS_SEED)} plus")
    print(f"  • 1 liquidación de ejemplo")
    print()
    print("Usuarios disponibles:")
    print("  admin@trace.dev / Admin123456!  (ADMIN + PROFESOR)")
    print("  target@test.com  / Target123456! (PROFESOR)")
    print("  admin2@test.com  / Admin123456!  (ADMIN)")
    print("  juan@test.com    / Test123456!   (ALUMNO)")
    print("  maria@test.com   / Test123456!   (ALUMNO)")
    print("  carlos@test.com  / Test123456!   (ALUMNO)")
    print()


if __name__ == "__main__":
    asyncio.run(main())
