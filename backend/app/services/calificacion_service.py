"""CalificacionService — importacion, procesamiento y finalizacion de calificaciones.

Implementa el flujo de preview + confirm para importar calificaciones
desde archivos xlsx/csv, y el procesamiento de finalizacion (RN-07, RN-08).
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models.asignacion import Asignacion
from app.models.calificacion import Calificacion
from app.models.entrada_padron import EntradaPadron
from app.models.enums import OrigenCalificacion
from app.models.version_padron import VersionPadron
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.calificacion_repository import CalificacionRepository
from app.repositories.entrada_padron_repository import EntradaPadronRepository
from app.repositories.umbral_materia_repository import UmbralMateriaRepository
from app.repositories.version_padron_repository import VersionPadronRepository
from app.services.calificacion_parsing import (
    _generar_preview_token,
    _preview_cache,
    columnas_identidad,
    detectar_columnas,
    parsear_csv,
    parsear_xlsx,
)


# ── Service ──────────────────────────────────────────────────────────


class CalificacionService:
    """Servicio de calificaciones — importacion y finalizacion."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.calificacion_repo = CalificacionRepository(session, tenant_id)
        self.umbral_repo = UmbralMateriaRepository(session, tenant_id)
        self.entrada_padron_repo = EntradaPadronRepository(
            session, EntradaPadron, tenant_id
        )
        self.version_padron_repo = VersionPadronRepository(
            session, VersionPadron, tenant_id
        )
        self.asignacion_repo = AsignacionRepository(
            session, Asignacion, tenant_id
        )

    # ── Preview ─────────────────────────────────────────────────────────

    async def importar_preview(
        self, archivo: bytes, filename: str, materia_id: UUID
    ) -> dict:
        """Procesa un archivo y retorna preview con token.

        Args:
            archivo: Contenido binario del archivo.
            filename: Nombre del archivo (para detectar formato).
            materia_id: UUID de la materia destino.

        Returns:
            Dict con actividades_detectadas, filas, alumnos_detectados,
            preview_token.
        """
        lower_name = filename.lower()
        if lower_name.endswith(".xlsx"):
            headers, filas = parsear_xlsx(archivo)
        elif lower_name.endswith(".csv"):
            headers, filas = parsear_csv(archivo)
        else:
            raise BusinessError(
                f"Formato no soportado: {filename}. Usar .xlsx o .csv"
            )

        if not filas:
            raise BusinessError("El archivo no contiene datos")

        preview_token = _generar_preview_token(archivo)
        columnas = detectar_columnas(headers, filas)

        _preview_cache[preview_token] = {
            "headers": headers,
            "filas": filas,
            "columnas": columnas,
            "materia_id": materia_id,
        }

        return {
            "actividades_detectadas": (
                columnas["numericas"] + columnas["textuales"]
            ),
            "filas": len(filas),
            "alumnos_detectados": len(filas),
            "preview_token": preview_token,
        }

    # ── Confirmar importacion ───────────────────────────────────────────

    async def importar_confirm(
        self,
        preview_token: str,
        materia_id: UUID,
        actividades_seleccionadas: list[str],
        usuario_id: UUID,
    ) -> dict:
        """Confirma la importacion y persiste las calificaciones.

        Args:
            preview_token: Token generado en el preview.
            materia_id: UUID de la materia destino.
            actividades_seleccionadas: Solo estas actividades se importan.
            usuario_id: UUID del usuario que importa.

        Returns:
            Dict con calificaciones_importadas y actividades.

        Raises:
            BusinessError: Si el token es invalido o expiro.
        """
        if preview_token not in _preview_cache:
            raise BusinessError(
                "Preview token invalido o expirado. Reintentar preview."
            )

        preview_data = _preview_cache.pop(preview_token)

        if preview_data.get("materia_id") != materia_id:
            raise BusinessError("El preview no corresponde a esta materia")

        headers = preview_data["headers"]
        filas = preview_data["filas"]
        columnas = preview_data["columnas"]

        actividades = (
            actividades_seleccionadas
            or columnas["numericas"] + columnas["textuales"]
        )

        # Resolver umbral una sola vez
        umbral_pct, valores_aprobatorios = await self._resolver_umbral(
            materia_id, usuario_id
        )

        # Identificar columnas de actividad
        es_actividad: dict[str, bool] = {}
        for col in columnas["numericas"]:
            es_actividad[col] = True
        for col in columnas["textuales"]:
            es_actividad[col] = True

        # Identificar columna de actividad numerica
        actividad_es_numerica: dict[str, bool] = {}
        for col in columnas["numericas"]:
            actividad_es_numerica[col] = True
        for col in columnas["textuales"]:
            actividad_es_numerica[col] = False

        # Identificar columnas de identidad
        cols_identidad = columnas_identidad()
        indices_identidad: dict[str, int] = {}
        for h in headers:
            if h.lower().strip() in cols_identidad:
                indices_identidad[h] = headers.index(h)

        calificaciones: list[Calificacion] = []
        actividades_count: dict[str, int] = {}

        for fila in filas:
            entrada_padron_id = await self._match_entrada_padron(
                fila, headers, indices_identidad
            )

            for actividad in actividades:
                if actividad not in headers:
                    continue

                idx = headers.index(actividad)
                raw_valor = fila[idx] if idx < len(fila) else ""
                if not raw_valor:
                    continue

                nota_numerica = None
                nota_textual = None

                if actividad_es_numerica.get(actividad, True):
                    try:
                        nota_numerica = Decimal(str(raw_valor))
                    except Exception:
                        nota_textual = raw_valor
                else:
                    nota_textual = raw_valor

                aprobado = self._evaluar_aprobado(
                    nota_numerica, nota_textual,
                    umbral_pct, valores_aprobatorios,
                )

                cal = Calificacion(
                    tenant_id=self.tenant_id,
                    entrada_padron_id=entrada_padron_id,
                    materia_id=materia_id,
                    actividad=actividad,
                    nota_numerica=nota_numerica,
                    nota_textual=nota_textual,
                    aprobado=aprobado,
                    origen=OrigenCalificacion.IMPORTADO,
                )
                calificaciones.append(cal)
                actividades_count[actividad] = (
                    actividades_count.get(actividad, 0) + 1
                )

        if calificaciones:
            await self.calificacion_repo.bulk_create(calificaciones)

        return {
            "calificaciones_importadas": len(calificaciones),
            "actividades": [
                {"nombre": name, "count": count}
                for name, count in actividades_count.items()
            ],
        }

    # ── Helpers internos ────────────────────────────────────────────────

    async def _resolver_umbral(
        self, materia_id: UUID, usuario_id: UUID
    ) -> tuple[int, list[str] | None]:
        """Resuelve umbral y valores aprobatorios para un usuario/materia.

        Returns:
            Tuple de (umbral_pct, valores_aprobatorios). Default: (60, None).
        """
        umbral_pct_defecto = 60
        try:
            from sqlalchemy import select  # noqa: PLC0415

            stmt = (
                select(Asignacion)
                .where(
                    Asignacion.usuario_id == usuario_id,
                    Asignacion.materia_id == materia_id,
                    Asignacion.tenant_id == self.tenant_id,
                    Asignacion.deleted_at.is_(None),
                )
                .limit(1)
            )
            result = await self.session.scalar(stmt)
            if result is not None:
                umbral = await self.umbral_repo.find_by_asignacion(result.id)
                if umbral is not None:
                    return umbral.umbral_pct, umbral.valores_aprobatorios
        except Exception:
            pass
        return umbral_pct_defecto, None

    @staticmethod
    def _evaluar_aprobado(
        nota_numerica: Decimal | None,
        nota_textual: str | None,
        umbral_pct: int,
        valores_aprobatorios: list[str] | None,
    ) -> bool:
        """Determina si una calificacion esta aprobada segun el umbral.

        Args:
            nota_numerica: Nota numerica o None.
            nota_textual: Nota textual o None.
            umbral_pct: Porcentaje minimo para aprobar.
            valores_aprobatorios: Valores textuales que se consideran aprobados.

        Returns:
            True si esta aprobada, False en otro caso.
        """
        # Si hay nota numerica, usar siempre ese criterio
        if nota_numerica is not None:
            return nota_numerica >= umbral_pct

        # Solo nota textual
        if nota_textual is not None and valores_aprobatorios:
            return nota_textual in valores_aprobatorios

        return False

    async def _match_entrada_padron(
        self,
        fila: list[str],
        headers: list[str],
        indices_identidad: dict[str, int],
    ) -> UUID:
        """Busca la EntradaPadron que corresponde a una fila del archivo.

        Intenta matchear por nombre/apellido contra entradas del padron
        del tenant.

        Raises:
            BusinessError: Si no se encuentra la entrada correspondiente.
        """
        nombre = ""
        apellido = ""

        for col_name, idx in indices_identidad.items():
            val = fila[idx] if idx < len(fila) else ""
            col_lower = col_name.lower().strip()
            if col_lower in ("nombre",):
                nombre = val
            elif col_lower in ("apellido", "apellidos"):
                apellido = val

        if not nombre and not apellido:
            raise BusinessError(
                "No se pudieron identificar columnas de nombre/apellido "
                "en el archivo"
            )

        try:
            entradas = await self.entrada_padron_repo.list_all()
            for ep in entradas:
                if (
                    ep.nombre.lower() == nombre.lower()
                    and ep.apellidos.lower() == apellido.lower()
                ):
                    return ep.id
        except Exception:
            pass

        raise BusinessError(
            f"No se encontro entrada de padron para {nombre} {apellido}. "
            "Importar el padron antes de las calificaciones."
        )

    # ── Procesar finalizacion (RN-07, RN-08) ────────────────────────────

    async def procesar_finalizacion(
        self, archivo: bytes, filename: str, materia_id: UUID
    ) -> dict:
        """Procesa un archivo de finalizacion y detecta entregas sin
        calificar.

        RN-07: Actividades textuales finalizadas sin calificacion
        se listan como "posibles sin corregir".
        RN-08: Actividades numericas sin calificacion se omiten
        (ausencia = no entregado).

        Args:
            archivo: Contenido binario del archivo.
            filename: Nombre del archivo.
            materia_id: UUID de la materia.

        Returns:
            Dict con posibles_sin_corregir.
        """
        lower_name = filename.lower()
        if lower_name.endswith(".xlsx"):
            headers, filas = parsear_xlsx(archivo)
        elif lower_name.endswith(".csv"):
            headers, filas = parsear_csv(archivo)
        else:
            raise BusinessError(
                f"Formato no soportado: {filename}. Usar .xlsx o .csv"
            )

        columnas = detectar_columnas(headers, filas)
        textuales = set(columnas["textuales"])

        existing = await self.calificacion_repo.list_by_materia(materia_id)

        posibles_sin_corregir: list[dict] = []

        for fila_idx, fila in enumerate(filas):
            for actividad in textuales:
                if actividad not in headers:
                    continue

                idx = headers.index(actividad)
                raw_valor = fila[idx] if idx < len(fila) else ""
                if not raw_valor:
                    continue

                # Verificar si ya existe calificacion para esta
                # combinacion entrada_padron + actividad
                entrada_id = None
                try:
                    entrada_id = await self._match_entrada_padron(
                        fila,
                        headers,
                        self._extraer_indices_identidad(headers),
                    )
                except BusinessError:
                    pass  # Sin padron, no se puede verificar si esta calificada

                ya_calificada = (
                    entrada_id is not None
                    and any(
                        c.actividad == actividad
                        and c.entrada_padron_id == entrada_id
                        for c in existing
                    )
                )

                if not ya_calificada:
                    nombre = fila[0] if fila else "?"
                    posibles_sin_corregir.append({
                        "alumno": nombre,
                        "actividad": actividad,
                        "entregado_en": raw_valor,
                    })

        return {
            "posibles_sin_corregir": posibles_sin_corregir,
        }

    def _extraer_indices_identidad(
        self, headers: list[str]
    ) -> dict[str, int]:
        cols = columnas_identidad()
        indices: dict[str, int] = {}
        for h in headers:
            if h.lower().strip() in cols:
                indices[h] = headers.index(h)
        return indices
