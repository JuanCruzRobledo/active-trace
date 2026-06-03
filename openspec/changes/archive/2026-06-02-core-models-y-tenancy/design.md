# Design: Core Models & Multi-Tenant Foundation (C-02)

## Architecture Decisions

### 1. Mixin Inheritance vs. Composition

**Decision**: SQLAlchemy mixin inheritance (declarative base pattern)

**Why**:
- Toda entidad futura heredará automáticamente `id`, `tenant_id`, timestamps y soft delete
- No requiere configuración por modelo; DRY
- SQLAlchemy 2.0 async soporta mixins nativamente
- Alternativa (composition) requeriría inyectar un objeto en cada modelo → más verboso y error-prone

**Implementation**:
```python
# backend/app/models/base.py
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, UUID, DateTime, Boolean
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from typing import Optional

class BaseMixin:
    """Mixin base: audit timestamps + soft delete + tenant scope"""
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(UUID, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

Base = declarative_base()

class BaseModel(Base, BaseMixin):
    """ORM base: todos los modelos heredan de aquí"""
    __abstract__ = True
```

**Constraints**:
- Archivo máx ~50 LOC (solo la estructura de mixin)
- Índices en `tenant_id` y `deleted_at` para performance de queries scoped

---

### 2. Repository Generic[T] Pattern & Tenant Scope

**Decision**: Generic repository with SQLAlchemy Type[T] constraint; tenant scope applied ALWAYS in where clause

**Why**:
- Type safety: `repo.find_by_id(id: UUID, tenant_id: UUID) -> T | None`
- Compile-time: si llamas un método que no filtra tenant_id, el type checker lo detecta (en teoría)
- Runtime: agregamos un `_apply_tenant_scope()` interno que inyecta `where(Model.tenant_id == tenant_id)` en TODA query
- Falla de seguridad = bug que pasa code review → pero con tests integration, lo cachamos

**Implementation**:
```python
# backend/app/repositories/base.py
from typing import TypeVar, Generic, Type, List, Optional
from uuid import UUID
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

T = TypeVar('T', bound='BaseModel')

class BaseRepository(Generic[T]):
    """Repositorio genérico: tenant scope SIEMPRE activo"""
    
    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model
    
    def _apply_tenant_scope(self, stmt):
        """Inyecta tenant_id en el where clause (privado, siempre se usa)"""
        return stmt.where(self.model.tenant_id == self.tenant_id)
    
    async def find_by_id(self, id: UUID, tenant_id: UUID) -> Optional[T]:
        """Buscar por PK; scope tenant obligatorio"""
        self.tenant_id = tenant_id
        stmt = select(self.model).where(
            and_(
                self.model.id == id,
                self.model.tenant_id == tenant_id,
                self.model.deleted_at.is_(None)  # Soft delete filter
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_all(self, tenant_id: UUID) -> List[T]:
        """Listar todos (activos) de un tenant"""
        self.tenant_id = tenant_id
        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == tenant_id,
                self.model.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def soft_delete(self, id: UUID, tenant_id: UUID) -> bool:
        """Marcar como eliminado (soft delete)"""
        obj = await self.find_by_id(id, tenant_id)
        if not obj:
            return False
        obj.deleted_at = datetime.utcnow()
        await self.session.commit()
        return True
```

**Constraints**:
- Máx 1 repository por agregado de dominio
- `find_*` SIEMPRE recibe `tenant_id` como parámetro
- `list_all()`, `create()`, `update()` SIEMPRE filtran/scopen tenant
- Nunca: `session.query(Model).filter(...)` — solo statements estructurados

**Code Review Gate**: un query sin `tenant_id` scope → rechazo inmediato

---

### 3. AES-256 Encryption Strategy

**Decision**: Use `cryptography.Fernet` (AES-128-CBC + HMAC) para compatibilidad, con clave de 32 bytes (256 bits)

**Why**:
- `cryptography.Fernet` es librería estándar, auditada, NIST-approved
- Implementación: AES-128 en modo CBC + HMAC-SHA256 (autenticado)
- Note: "AES-256" en el spec se refiere al tamaño de clave (32 bytes), no al modo de operación
- Alternativas: `PyCryptodome` (más low-level), `pyca/nacl` (mejor para secretos, pero overkill aquí)
- Razón elegida: Fernet balancea seguridad + usabilidad + performance

**Key Management**:
- `ENCRYPTION_KEY` env var: debe ser 32 bytes (base64 o hex)
- Nunca hardcodeado; nunca en logs; nunca en git
- En `.env.local` (gitignore) para dev; en secret manager (Vault/AWS Secrets) en prod

**Implementation**:
```python
# backend/app/core/security.py
from cryptography.fernet import Fernet
import os
from typing import Optional

class EncryptionService:
    """AES-256 (Fernet) encryption para PII en reposo"""
    
    def __init__(self, key: Optional[bytes] = None):
        if key is None:
            key_str = os.getenv("ENCRYPTION_KEY")
            if not key_str:
                raise ValueError("ENCRYPTION_KEY not set")
            # Assume key_str is base64-encoded 32 bytes
            key = base64.b64decode(key_str)
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext -> base64 ciphertext"""
        if not plaintext:
            return None
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext -> plaintext"""
        if not ciphertext:
            return None
        return self.cipher.decrypt(ciphertext.encode()).decode()
```

**Fields encrypted** (column-level):
- `Usuario.email` (marked `[cifrado]` in KB)
- `Usuario.dni`
- `Usuario.cuil`
- `Usuario.cbu`
- `Usuario.alias_cbu`

**At-rest encryption**: datos en BD están encriptados; descifrados solo en memoria cuando se usan
**Logging**: JAMÁS loguear valores descifrados; siempre registrar acciones (quién leyó, cuándo)

---

### 4. Alembic Migration Structure

**Decision**: Una migración por cambio de schema. Migration 001 crea `tenant` table.

**Why**:
- Trazabilidad: cada cambio de BD tiene un commit de migración asociado
- Rollback limpio: `alembic downgrade 001` revierte exactamente lo que 001 hizo
- Versioning: future migrations build on top (002, 003, etc.)

**Implementation**:
```sql
-- backend/alembic/versions/001_tenant.py (auto-generated, editado manualmente si es necesario)
revision = '001_tenant'
down_revision = None

def upgrade():
    op.create_table(
        'tenant',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('domain', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('domain'),
        sa.Index('ix_tenant_deleted_at', 'deleted_at')
    )

def downgrade():
    op.drop_table('tenant')
```

**Convention**:
- `backend/alembic/versions/{NNN}_{change_name}.py`
- Nombres auto-generados por `alembic revision --autogenerate -m "{change_name}"`
- Revisar y editar a mano si es necesario
- Un cambio de schema = una migración; no consolidar

**Constraints**:
- Máx 1 migración por PR/commit (si necesitás 2, son 2 commits)
- Migrations NUNCA borrarse una vez creadas (inmutabilidad del histórico)
- Tests: run migration 001, verify table exists, rollback, verify dropped

---

### 5. Soft Delete Implementation

**Decision**: `deleted_at` timestamp column; queries filtran `where deleted_at is null` por defecto

**Why**:
- Auditoría: cuándo se borró, NO se pierde
- Recuperación: puedo "undelete" seteando `deleted_at = null`
- Datos históricos: reportes pueden incluir borrados si lo necesitan (audit trail)
- Alternativa: flag booleano `is_deleted` — menos informativo

**Implementation**:
```python
# En BaseMixin (arriba)
deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

# En Repository
async def soft_delete(self, id: UUID, tenant_id: UUID) -> bool:
    """Soft delete: mark with deleted_at timestamp"""
    obj = await self.find_by_id(id, tenant_id)
    if not obj:
        return False
    obj.deleted_at = datetime.utcnow()
    await self.session.commit()
    return True

async def list_all(self, tenant_id: UUID) -> List[T]:
    """By default, exclude soft-deleted (active only)"""
    stmt = select(self.model).where(
        and_(
            self.model.tenant_id == tenant_id,
            self.model.deleted_at.is_(None)  # Soft delete filter
        )
    )
    result = await self.session.execute(stmt)
    return result.scalars().all()

async def list_all_including_deleted(self, tenant_id: UUID) -> List[T]:
    """For admin audit view: include soft-deleted"""
    stmt = select(self.model).where(
        self.model.tenant_id == tenant_id
    )
    result = await self.session.execute(stmt)
    return result.scalars().all()
```

**Constraint**: Nunca hard delete. Si necesitás limpiar datos (GDPR right-to-be-forgotten), creas una entidad nula con `deleted_at` muy antiguo, no borrás.

---

## Technical Constraints & Assumptions

1. **DB**: PostgreSQL 15+; `uuid-ossp` extension (or use Python UUID generation)
2. **SQLAlchemy**: 2.0+ con async support
3. **Python**: 3.13+ (type hints, match/case)
4. **Encryption Key Format**: base64-encoded 32-byte string (pasado via ENCRYPTION_KEY env var)
5. **Test DB**: contenedor ephemeral (se crea y destruye por test suite)
6. **Code Review**: un query sin tenant_id scope = rechazo automático

---

## Open Questions

1. **Tenant model fields**: ¿Qué datos almacena un Tenant aparte de id + name? (dominio, plan de suscripción, branding, etc.) → resuelto en KB §2, solo id + name + domain por ahora
2. **Encryption key rotation**: ¿Cómo re-encriptar registros viejos con nueva clave? → fuera de scope C-02; entra en C-19 u operacional después
3. **Audit log de soft deletes**: ¿Logueo a audit table quién borró y por qué? → sí, en C-05 audit-log; por ahora solo timestamp en deleted_at
