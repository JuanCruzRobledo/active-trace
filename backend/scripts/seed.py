"""Seed script para desarrollo — unifica la creación de datos de prueba.

Crea (si no existen):
  • Tenant de desarrollo (id: 00000000-0000-0000-0000-000000000001)
  • Roles: ADMIN, PROFESOR, TUTOR, COORDINADOR, ALUMNO
  • Permisos globales del sistema + asignación a roles
  • admin@trace.dev / Admin123456!  (roles: ADMIN, PROFESOR)
  • target@test.com  / Target123456! (rol: PROFESOR)
  • admin2@test.com  / Admin123456!  (rol: ADMIN)
  • Estructura académica: carrera, materia, cohorte
  • Asignación del profesor a la materia + umbral
  • 3 alumnos (juan, maria, carlos) con calificaciones

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
from app.core.security import hash_password
from app.models.asignacion import Asignacion
from app.models.calificacion import Calificacion
from app.models.entrada_padron import EntradaPadron
from app.models.permiso import Permiso
from app.models.umbral_materia import UmbralMateria
from app.models.usuario import Usuario
from app.models.version_padron import VersionPadron
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
]

# QUÉ permisos tiene cada rol
ROLE_PERMISOS: dict[str, list[str]] = {
    "ADMIN": [p[0] for p in PERMISOS],  # Todos
    "COORDINADOR": ["atrasados:ver", "equipos:ver", "equipos:asignar"],
    "PROFESOR": ["atrasados:ver", "equipos:ver"],
    "TUTOR": ["atrasados:ver"],
    "ALUMNO": [],
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


async def ensure_materia(session, carrera_id: UUID) -> UUID:
    """Crea una materia de prueba si no existe."""
    codigo = "AM-I"
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
            "nom": "Análisis Matemático I",
        },
    )
    print(f"  [+] Materia {codigo} creada")
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
    """Crea umbral de aprobación si no existe."""
    result = await session.execute(
        text(
            "SELECT id FROM umbral_materia "
            "WHERE materia_id = :mid AND tenant_id = :tid AND deleted_at IS NULL"
        ),
        {"mid": materia_id, "tid": DEV_TENANT_ID},
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
        materia_id = await ensure_materia(session, carrera_id)
        cohorte_id = await ensure_cohorte(session, carrera_id)

        # ── 6. Asignación profesor + umbral ──────────────────────────
        print()
        # Buscar UUID del profesor en tabla `usuario` (FK de asignacion)
        prof_result = await session.execute(
            text("SELECT id FROM usuario WHERE auth_user_id = :auid"),
            {"auid": main_user_ids.get("target@test.com")},
        )
        prof_row = prof_result.fetchone()
        if prof_row:
            asignacion_id = await ensure_asignacion_profesor(
                session, materia_id, prof_row[0]
            )
            await ensure_umbral(session, asignacion_id, materia_id)
        else:
            print("  [!] No se encontró target@test.com, saltando asignación profesor")

        # ── 7. Alumnos ───────────────────────────────────────────────
        print()
        alumno_usuarios: list[dict] = []
        for alumno in ALUMNOS:
            auth_uid, usuario_id = await ensure_alumno_user(session, alumno, role_ids)
            alumno_usuarios.append({
                "auth_uid": auth_uid,
                "usuario_id": usuario_id,
                "nombre": alumno["nombre"],
                "apellidos": alumno["apellidos"],
                "email": alumno["email"],
                "comision": alumno["comision"],
                "regional": alumno["regional"],
            })

        # ── 8. Versión padron + entradas ─────────────────────────────
        print()
        if prof_row:
            version_id = await ensure_version_padron(
                session, materia_id, cohorte_id, prof_row[0]
            )
        else:
            # fallback: usar admin como cargado_por
            admin_result = await session.execute(
                text("SELECT id FROM users WHERE email = 'admin@trace.dev'"),
            )
            admin_row = admin_result.fetchone()
            version_id = await ensure_version_padron(
                session, materia_id, cohorte_id, admin_row[0]
            )

        entradas: list[dict] = []
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
            entradas.append({
                "entrada_id": eid,
                "usuario_id": au["usuario_id"],
                "nombre": au["nombre"],
                "apellidos": au["apellidos"],
            })

        # ── 9. Calificaciones ────────────────────────────────────────
        print()
        await ensure_calificaciones(session, materia_id, entradas)

        # ── Commit ───────────────────────────────────────────────────
        await session.commit()

    await close_engine()

    total_usuarios = len(USERS) + len(ALUMNOS)
    print(f"\n[OK] Seed completado.")
    print(f"  • {total_usuarios} usuarios creados")
    print(f"  • {len(PERMISOS)} permisos + asignación a roles")
    print(f"  • 1 carrera, 1 materia, 1 cohorte")
    print(f"  • {len(entradas)} entradas de padrón")
    print(f"  • Calificaciones de prueba")
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
