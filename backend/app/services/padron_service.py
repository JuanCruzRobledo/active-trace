"""PadronService — logica de negocio para importacion y gestion de padrones.

Implementa el versionado de padron (VersionPadron → EntradaPadron),
importacion manual con preview + confirm, matching por email contra
usuarios existentes, y vaciado de materia (F1.5, RN-04).
"""

from __future__ import annotations

import hashlib
import io
import csv
import json
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models.entrada_padron import EntradaPadron
from app.models.usuario import Usuario
from app.models.version_padron import VersionPadron
from app.repositories.entrada_padron_repository import EntradaPadronRepository
from app.repositories.version_padron_repository import VersionPadronRepository


# ── Cache de previews en memoria (volatil, por servidor) ──────────────
# En produccion con multiples workers, reemplazar por Redis/Cache compartido.
_preview_cache: dict[str, dict[str, Any]] = {}


def _generar_preview_token(data: bytes) -> str:
    """Genera un token unico basado en el contenido del archivo."""
    return hashlib.sha256(data).hexdigest()


def _parsear_xlsx(data: bytes) -> list[dict[str, str | None]]:
    """Parsea un archivo xlsx y retorna lista de dicts."""
    try:
        import openpyxl  # noqa: PLC0415
    except ImportError:
        raise BusinessError("openpyxl no esta instalado. Instalarlo con: pip install openpyxl")

    workbook = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    sheet = workbook.active
    if sheet is None:
        raise BusinessError("El archivo xlsx no contiene ninguna hoja")

    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        raise BusinessError("El archivo xlsx esta vacio")

    headers = [str(h) if h is not None else "" for h in rows[0]]
    registros: list[dict[str, str | None]] = []
    for row in rows[1:]:
        registro: dict[str, str | None] = {}
        for i, header in enumerate(headers):
            val = row[i] if i < len(row) else None
            registro[header] = str(val) if val is not None else None
        registros.append(registro)

    return registros


def _parsear_csv(data: bytes) -> list[dict[str, str | None]]:
    """Parsea un archivo csv y retorna lista de dicts."""
    content = data.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    registros: list[dict[str, str | None]] = []
    for row in reader:
        registro: dict[str, str | None] = {}
        for key, val in row.items():
            registro[key.strip()] = val.strip() if val else None
        registros.append(registro)
    return registros


def _detectar_columnas(
    registros: list[dict[str, str | None]],
) -> list[str]:
    """Detecta y retorna las columnas mapeadas del archivo."""
    if not registros:
        return []
    return list(registros[0].keys())


class PadronService:
    """Servicio de padron de alumnos."""

    # Columnas esperadas para el mapeo
    COLUMNAS_ESPERADAS = {"nombre", "apellido", "email"}

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.version_repo = VersionPadronRepository(session, VersionPadron, tenant_id)
        self.entrada_repo = EntradaPadronRepository(session, EntradaPadron, tenant_id)

    # ── Preview ─────────────────────────────────────────────────────────

    async def preview_importacion(
        self, data: bytes, filename: str
    ) -> dict[str, Any]:
        """Procesa un archivo y devuelve preview con token.

        Args:
            data: Contenido binario del archivo.
            filename: Nombre del archivo (para detectar formato).

        Returns:
            Dict con preview_token, filas_detectadas, columnas_mapeadas, registros.
        """
        # Detectar formato por extension
        lower_name = filename.lower()
        if lower_name.endswith(".xlsx"):
            registros = _parsear_xlsx(data)
        elif lower_name.endswith(".csv"):
            registros = _parsear_csv(data)
        else:
            raise BusinessError(
                f"Formato no soportado: {filename}. Usar .xlsx o .csv"
            )

        if not registros:
            raise BusinessError("El archivo no contiene datos")

        columnas = _detectar_columnas(registros)
        preview_token = _generar_preview_token(data)

        # Almacenar en cache para validacion posterior
        _preview_cache[preview_token] = {
            "registros": registros,
            "columnas": columnas,
        }

        return {
            "preview": True,
            "preview_token": preview_token,
            "filas_leidas": len(registros),
            "columnas_mapeadas": columnas,
            "filas": registros[:20],  # Solo primeras 20 filas en preview
        }

    # ── Confirmar importacion ────────────────────────────────────────────

    async def confirmar_importacion(
        self,
        preview_token: str,
        materia_id: UUID,
        cohorte_id: UUID,
        cargado_por: UUID,
    ) -> VersionPadron:
        """Confirma una importacion y persiste los datos.

        Args:
            preview_token: Token generado en el preview.
            materia_id: UUID de la materia destino.
            cohorte_id: UUID de la cohorte destino.
            cargado_por: UUID del usuario que carga.

        Returns:
            La VersionPadron creada.

        Raises:
            BusinessError: Si el token es invalido o expiro.
        """
        if preview_token not in _preview_cache:
            raise BusinessError("Preview token invalido o expirado. Reintentar preview.")

        preview_data = _preview_cache.pop(preview_token)
        registros = preview_data["registros"]

        # Desactivar versiones anteriores
        await self.version_repo.desactivar_anteriores(materia_id, cohorte_id)

        # Crear nueva version
        version = VersionPadron(
            id=uuid4(),
            tenant_id=self.tenant_id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            cargado_por=cargado_por,
            activa=True,
        )
        await self.version_repo.save(version)

        # Crear entradas y hacer matching por email
        for registro in registros:
            email = registro.get("email", "").strip().lower() if registro.get("email") else ""
            nombre = registro.get("nombre", "") or ""
            apellido = registro.get("apellido", registro.get("apellidos", "")) or ""

            # Buscar usuario por email en el mismo tenant
            usuario_id = await self._match_usuario_por_email(email)

            entrada = EntradaPadron(
                id=uuid4(),
                tenant_id=self.tenant_id,
                version_id=version.id,
                usuario_id=usuario_id,
                nombre=nombre,
                apellidos=apellido,
                email=email,
                comision=registro.get("comision") or registro.get("comisión") or registro.get("grupo"),
                regional=registro.get("regional") or registro.get("sede"),
            )
            await self.entrada_repo.save(entrada)

        return version

    async def _match_usuario_por_email(
        self, email: str
    ) -> Optional[UUID]:
        """Busca un usuario por email dentro del mismo tenant.

        Args:
            email: Email a buscar.

        Returns:
            UUID del usuario o None si no se encuentra.
        """
        if not email:
            return None

        from sqlalchemy import and_  # noqa: PLC0415

        stmt = (
            select(Usuario)
            .where(
                and_(
                    Usuario.tenant_id == self.tenant_id,
                    Usuario.deleted_at.is_(None),
                )
            )
            .limit(500)
        )
        result = await self.session.scalars(stmt)
        usuarios = list(result.all())

        for usuario in usuarios:
            # Email esta cifrado, usamos el descifrado explicito
            try:
                from app.core.encryption import EncryptionService  # noqa: PLC0415
                enc = EncryptionService()
                email_plano = enc.decrypt(usuario.email)
                if email_plano and email_plano.strip().lower() == email:
                    return usuario.id
            except Exception:
                continue

        return None

    # ── Consulta ─────────────────────────────────────────────────────────

    async def obtener_activo(
        self, materia_id: UUID, cohorte_id: UUID
    ) -> Optional[VersionPadron]:
        """Retorna la version activa del padron con sus entradas."""
        version = await self.version_repo.get_activa(materia_id, cohorte_id)
        if version is None:
            return None

        entradas = await self.entrada_repo.listar_por_version(version.id)
        version.entradas = entradas  # type: ignore[attr-defined]
        return version

    async def listar_versiones(
        self, materia_id: UUID, cohorte_id: UUID
    ) -> list[VersionPadron]:
        """Retorna todas las versiones de una materia x cohorte."""
        return await self.version_repo.listar_por_materia(materia_id, cohorte_id)

    # ── Vaciar materia (F1.5, RN-04) ────────────────────────────────────

    async def vaciar_materia(
        self, materia_id: UUID
    ) -> dict[str, int]:
        """Vacia datos de ingesta de una materia.

        Desactiva todas las versiones activas y elimina entradas asociadas.
        No afecta otras materias (RN-04).

        Args:
            materia_id: UUID de la materia a vaciar.

        Returns:
            Dict con versiones_desactivadas y entradas_eliminadas.
        """
        # Obtener todas las versiones activas de la materia
        from sqlalchemy import and_  # noqa: PLC0415

        stmt = (
            select(VersionPadron)
            .where(
                and_(
                    VersionPadron.materia_id == materia_id,
                    VersionPadron.tenant_id == self.tenant_id,
                    VersionPadron.activa.is_(True),
                    VersionPadron.deleted_at.is_(None),
                )
            )
        )
        result = await self.session.scalars(stmt)
        versiones = list(result.all())
        version_ids = [v.id for v in versiones]
        total_versiones = len(versiones)

        # Eliminar entradas de esas versiones
        await self.entrada_repo.eliminar_por_materia(materia_id, version_ids)

        # Desactivar versiones
        for version in versiones:
            version.activa = False
            await self.session.flush()

        return {
            "versiones_desactivadas": total_versiones,
            "entradas_eliminadas": 0,  # Se retorna el total real desde el router
        }
