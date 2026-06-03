"""Repositorio genérico con scope de tenant obligatorio.

Todo repositorio del dominio SHALL heredar de :class:`BaseRepository` para
garantizar que:

- **Toda query** filtra por ``tenant_id`` (aislamiento row-level multi-tenant).
- **Toda query** excluye registros soft-delete por defecto.
- El scope de tenant se asigna al construir el repositorio, NUNCA por parámetro
  de request.

Uso::

    class UsuarioRepository(BaseRepository[Usuario]):
        pass

    repo = UsuarioRepository(session=db, model=Usuario, tenant_id=current_tenant.id)
    usuarios = await repo.list_all()
"""

from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select


T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Repositorio genérico con scope de tenant obligatorio.

    Attributes:
        session: Sesión async de SQLAlchemy.
        model: Clase del modelo ORM.
        tenant_id: UUID del tenant — filtra TODAS las queries.
    """

    def __init__(
        self,
        session: AsyncSession | None,
        model: type[T],
        tenant_id: Any,  # uuid.UUID en runtime
    ) -> None:
        self.session = session
        self.model = model
        self.tenant_id = tenant_id

    # ── Query scoping ──────────────────────────────────────────────────────

    def _scope_query(self, stmt: Select[Any]) -> Select[Any]:
        """Aplica scope de tenant + soft-delete a una query existente.

        El scope de tenant SIEMPRE se aplica. Un query sin este filtro
        es un bug que debe fallar en code review.

        Args:
            stmt: Query SQLAlchemy a scopear.

        Returns:
            Query con filtros ``tenant_id`` y ``deleted_at IS NULL``.
        """
        conditions: list[Any] = [
            self.model.tenant_id == self.tenant_id  # type: ignore[attr-defined]
        ]

        # Soft-delete scope: excluir registros eliminados por defecto
        if hasattr(self.model, "deleted_at"):
            conditions.append(
                self.model.deleted_at.is_(None)  # type: ignore[attr-defined]
            )

        return stmt.where(and_(*conditions))

    def _list_query(self) -> Select[Any]:
        """Query base para listar registros activos del modelo."""
        return select(self.model)

    # ── Public API ─────────────────────────────────────────────────────────

    async def get_by_id(self, id: Any) -> Optional[T]:
        """Retorna un registro activo por su PK, scoped al tenant.

        Args:
            id: UUID del registro.

        Returns:
            Instancia del modelo o ``None`` si no existe o está soft-delete.
        """
        stmt = self._scope_query(
            select(self.model).where(
                self.model.id == id  # type: ignore[attr-defined]
            )
        )
        result = await self.session.scalar(stmt)  # type: ignore[union-attr]
        return result  # type: ignore[no-any-return]

    async def list_all(self) -> list[T]:
        """Retorna todos los registros activos del tenant.

        Returns:
            Lista de instancias del modelo (vacía si no hay registros).
        """
        stmt = self._scope_query(self._list_query())
        result = await self.session.scalars(stmt)  # type: ignore[union-attr]
        return list(result.all())

    async def save(self, instance: T) -> T:
        """Persiste una instancia (insert o update) en la sesión actual.

        Args:
            instance: Instancia del modelo a persistir.

        Returns:
            La misma instancia con el session.add() aplicado.
        """
        if self.session is not None:
            self.session.add(instance)
            await self.session.flush()
        return instance

    async def soft_delete(self, instance: T) -> None:
        """Marca un registro como eliminado (soft delete).

        NO elimina físicamente. Setea ``deleted_at`` y persiste.

        Args:
            instance: Instancia del modelo a soft-delete.
        """
        instance.deleted_at = datetime.now(timezone.utc)  # type: ignore[attr-defined]
        await self.save(instance)
