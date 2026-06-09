"""003 — Create rol, permiso, rol_permiso tables + seed data

Revision ID: 003
Revises: 002
Create Date: 2026-06-02

C-04 rbac-permisos-finos: implementa el catalogo de roles y permisos
finos modulo:accion con la matriz rol x permiso para el tenant dev.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Constantes
_DEV_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    """Create rol, permiso, rol_permiso tables and seed data."""

    # ── permiso (global catalog, no tenant_id) ─────────────────────────
    op.create_table(
        "permiso",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("codigo", sa.String(100), nullable=False),
        sa.Column("descripcion", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("codigo", name="uq_permiso_codigo"),
    )

    # ── rol (tenant-scoped, soft delete) ───────────────────────────────
    op.create_table(
        "rol",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("codigo", sa.String(50), nullable=False),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "tenant_id", "codigo", name="uq_rol_tenant_codigo"
        ),
        sa.UniqueConstraint(
            "tenant_id", "nombre", name="uq_rol_tenant_nombre"
        ),
    )
    op.create_index("ix_rol_tenant_id", "rol", ["tenant_id"])

    # ── rol_permiso (tenant-scoped matrix) ─────────────────────────────
    op.create_table(
        "rol_permiso",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "rol_id",
            UUID(as_uuid=True),
            sa.ForeignKey("rol.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "permiso_id",
            UUID(as_uuid=True),
            sa.ForeignKey("permiso.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "rol_id",
            "permiso_id",
            name="uq_rol_permiso_tenant_rol_permiso",
        ),
    )
    op.create_index(
        "ix_rol_permiso_tenant_id", "rol_permiso", ["tenant_id"]
    )
    op.create_index(
        "ix_rol_permiso_rol_id", "rol_permiso", ["rol_id"]
    )
    op.create_index(
        "ix_rol_permiso_permiso_id", "rol_permiso", ["permiso_id"]
    )

    # ═══════════════════════════════════════════════════════════════════
    # SEED DATA
    # ═══════════════════════════════════════════════════════════════════

    conn = op.get_bind()

    # ── Insertar 25 permisos ──────────────────────────────────────────
    permisos = [
        ("ver_estado_academico", "Ver estado academico propio"),
        ("reservar_evaluacion", "Reservar instancia de evaluacion"),
        ("confirmar_avisos", "Confirmar avisos (acknowledgment)"),
        ("calificaciones:importar", "Importar calificaciones"),
        ("atrasados:ver", "Ver alumnos atrasados"),
        ("entregas_sin_corregir", "Detectar entregas sin corregir"),
        ("comunicacion:enviar", "Enviar comunicaciones a alumnos"),
        ("comunicacion:aprobar", "Aprobar comunicaciones masivas"),
        ("encuentros:gestionar", "Gestionar encuentros"),
        ("guardias:registrar", "Registrar guardias"),
        ("tareas:gestionar", "Gestionar tareas internas"),
        ("avisos:publicar", "Publicar avisos"),
        ("equipos:asignar", "Gestionar equipos docentes"),
        ("estructura:gestionar", "Gestionar estructura academica"),
        ("usuarios:gestionar", "Gestionar usuarios del tenant"),
        ("auditoria:ver", "Ver auditoria"),
        ("impersonacion:usar", "Usar impersonalizacion"),
        ("grilla_salarial:operar", "Operar grilla salarial"),
        ("liquidaciones:calcular", "Calcular liquidaciones"),
        ("liquidaciones:cerrar", "Cerrar liquidaciones"),
        ("liquidaciones:exportar", "Exportar liquidaciones"),
        ("liquidaciones:ver", "Ver liquidaciones"),
        ("facturas:gestionar", "Gestionar facturas"),
        ("tenant:configurar", "Configurar el tenant"),
    ]
    # Dict codigo → permiso_id
    permiso_ids = {}
    for codigo, descripcion in permisos:
        result = conn.execute(
            sa.text(
                "INSERT INTO permiso (id, codigo, descripcion, created_at) "
                "VALUES (gen_random_uuid(), :codigo, :descripcion, now()) "
                "RETURNING id"
            ),
            {"codigo": codigo, "descripcion": descripcion},
        )
        permiso_ids[codigo] = result.scalar_one()

    # ── Insertar 7 roles para tenant dev ──────────────────────────────
    roles_def = [
        ("ALUMNO", "Alumno", "Estudiante que cursa materias"),
        ("TUTOR", "Tutor", "Auxiliar / ayudante de catedra"),
        ("PROFESOR", "Profesor", "Docente a cargo de una o mas comisiones"),
        (
            "COORDINADOR",
            "Coordinador",
            "Responsable de un conjunto de materias o cohorte",
        ),
        (
            "NEXO",
            "Nexo",
            "Articulacion / enlace transversal entre la institucion y docentes",
        ),
        (
            "ADMIN",
            "Administrador",
            "Administrador del sistema dentro del tenant",
        ),
        (
            "FINANZAS",
            "Finanzas",
            "Responsable de liquidaciones y honorarios",
        ),
    ]
    rol_ids = {}
    for codigo, nombre, descripcion in roles_def:
        result = conn.execute(
            sa.text(
                "INSERT INTO rol (id, tenant_id, codigo, nombre, "
                "descripcion, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :tenant_id, :codigo, :nombre, "
                ":descripcion, now(), now()) RETURNING id"
            ),
            {
                "tenant_id": _DEV_TENANT_ID,
                "codigo": codigo,
                "nombre": nombre,
                "descripcion": descripcion,
            },
        )
        rol_ids[codigo] = result.scalar_one()

    # ── Insertar matriz rol x permiso ─────────────────────────────────
    # (rol_codigo, lista_de_permisos_codigos)
    matrix = [
        ("ALUMNO", ["ver_estado_academico", "reservar_evaluacion", "confirmar_avisos"]),
        ("TUTOR", [
            "confirmar_avisos",
            "atrasados:ver",
            "entregas_sin_corregir",
            "encuentros:gestionar",
            "guardias:registrar",
        ]),
        ("PROFESOR", [
            "confirmar_avisos",
            "calificaciones:importar",
            "atrasados:ver",
            "entregas_sin_corregir",
            "comunicacion:enviar",
            "encuentros:gestionar",
            "guardias:registrar",
            "tareas:gestionar",
        ]),
        ("COORDINADOR", [
            "confirmar_avisos",
            "calificaciones:importar",
            "atrasados:ver",
            "entregas_sin_corregir",
            "comunicacion:enviar",
            "comunicacion:aprobar",
            "encuentros:gestionar",
            "guardias:registrar",
            "tareas:gestionar",
            "avisos:publicar",
            "equipos:asignar",
            "auditoria:ver",
        ]),
        # NEXO: articulacion transversal — union de TUTOR + COORDINADOR
        ("NEXO", [
            "confirmar_avisos",
            "calificaciones:importar",
            "atrasados:ver",
            "entregas_sin_corregir",
            "comunicacion:enviar",
            "comunicacion:aprobar",
            "encuentros:gestionar",
            "guardias:registrar",
            "tareas:gestionar",
            "avisos:publicar",
            "equipos:asignar",
            "auditoria:ver",
        ]),
        # ADMIN: ALL except liquidaciones and facturas
        ("ADMIN", [
            "ver_estado_academico",
            "confirmar_avisos",
            "calificaciones:importar",
            "atrasados:ver",
            "entregas_sin_corregir",
            "comunicacion:enviar",
            "comunicacion:aprobar",
            "encuentros:gestionar",
            "guardias:registrar",
            "tareas:gestionar",
            "avisos:publicar",
            "equipos:asignar",
            "estructura:gestionar",
            "usuarios:gestionar",
            "auditoria:ver",
            "impersonacion:usar",
            "tenant:configurar",
        ]),
        ("FINANZAS", [
            "confirmar_avisos",
            "auditoria:ver",
            "grilla_salarial:operar",
            "liquidaciones:calcular",
            "liquidaciones:cerrar",
            "liquidaciones:exportar",
            "liquidaciones:ver",
            "facturas:gestionar",
        ]),
    ]

    for rol_codigo, permisos_codigos in matrix:
        for perm_codigo in permisos_codigos:
            conn.execute(
                sa.text(
                    "INSERT INTO rol_permiso (id, tenant_id, rol_id, "
                    "permiso_id, created_at) "
                    "VALUES (gen_random_uuid(), :tenant_id, :rol_id, "
                    ":permiso_id, now())"
                ),
                {
                    "tenant_id": _DEV_TENANT_ID,
                    "rol_id": rol_ids[rol_codigo],
                    "permiso_id": permiso_ids[perm_codigo],
                },
            )


def downgrade() -> None:
    """Drop tables in reverse order."""
    op.drop_index("ix_rol_permiso_permiso_id", table_name="rol_permiso")
    op.drop_index("ix_rol_permiso_rol_id", table_name="rol_permiso")
    op.drop_index("ix_rol_permiso_tenant_id", table_name="rol_permiso")
    op.drop_table("rol_permiso")
    op.drop_index("ix_rol_tenant_id", table_name="rol")
    op.drop_table("rol")
    op.drop_table("permiso")
