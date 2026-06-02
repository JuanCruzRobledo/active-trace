# Spec: Core Models & Multi-Tenant Foundation (C-02)

## Capability: tenant-isolation

### Requirement T-01: Tenant Model

**User Story**: Como sistema, necesito representar una institución (tenant) como raíz de aislamiento de datos.

**Scenario 1.1 — Crear instancia de Tenant**
```gherkin
Given un objeto Tenant con id, name, domain
When se instantia el modelo
Then tiene atributos: id (UUID), name (str), domain (str), created_at, updated_at, deleted_at
And created_at ≠ None, updated_at ≠ None, deleted_at == None
```

**Scenario 1.2 — Persistir Tenant en BD**
```gherkin
Given una instancia de Tenant: Tenant(id=UUID, name="UTN", domain="utn.edu.ar")
When se persiste en BD (INSERT)
Then row existe en tabla tenant con los valores correctos
And created_at, updated_at son timestamps válidos
```

---

### Requirement T-02: Multi-Tenant Isolation in Queries

**User Story**: Como repository, necesito garantizar que queries filtren siempre por tenant_id y nunca mezclen datos entre tenants.

**Scenario 2.1 — Repository filtra tenant_id por defecto**
```gherkin
Given dos tenants: T1 (id=uuid1), T2 (id=uuid2)
And una entidad de prueba (DummyEntity) en T1: obj1
And una entidad de prueba en T2: obj2
When llamo repo.list_all(tenant_id=uuid1)
Then retorna [obj1]
And no incluye obj2 (pertenece a otro tenant)
```

**Scenario 2.2 — Find by ID respeta tenant scope**
```gherkin
Given DummyEntity obj1 con id=id1, tenant_id=uuid1
And DummyEntity obj2 con id=id2, tenant_id=uuid2
When llamo repo.find_by_id(id=id1, tenant_id=uuid2)
Then retorna None (aunque id existe, pertenece a otro tenant)
```

**Scenario 2.3 — Prevenir query sin tenant_id (code review gate)**
```gherkin
Given un repositorio con método list_all()
When se intenta llamar list_all() sin parámetro tenant_id
Then el type checker detecta error (missing required param)
And en runtime, falla si tenant_id no se inyecta
```

---

## Capability: soft-delete

### Requirement SD-01: Soft Delete Mixin

**User Story**: Como auditoria, necesito que borrados sean reversibles y trazables (nunca hard delete).

**Scenario 3.1 — Entidad con soft delete flag**
```gherkin
Given una entidad (DummyEntity) que hereda BaseMixin
Then tiene atributo deleted_at: Optional[datetime]
And deleted_at == None por defecto (sin borrar)
```

**Scenario 3.2 — Soft delete marca con timestamp**
```gherkin
Given DummyEntity obj con id=id1, tenant_id=t1, deleted_at=None
When llamo repo.soft_delete(id=id1, tenant_id=t1)
Then obj.deleted_at == datetime.utcnow() (aproximadamente)
And row en BD tiene deleted_at ≠ None
```

**Scenario 3.3 — Queries excluyen soft-deleted por defecto**
```gherkin
Given DummyEntity obj1 (active, deleted_at=None)
And DummyEntity obj2 (soft-deleted, deleted_at=datetime(2026-06-02))
When llamo repo.list_all(tenant_id=t1)
Then retorna [obj1]
And no incluye obj2 (filtrado por deleted_at is not None)
```

**Scenario 3.4 — Admin puede ver borrados**
```gherkin
Given obj1 (activo), obj2 (soft-deleted)
When llamo repo.list_all_including_deleted(tenant_id=t1)
Then retorna [obj1, obj2]
```

**Scenario 3.5 — Soft deleted no se busca por ID**
```gherkin
Given DummyEntity obj (soft-deleted, id=id1, tenant_id=t1)
When llamo repo.find_by_id(id=id1, tenant_id=t1)
Then retorna None (aunque existe físicamente, está marcado como borrado)
```

---

## Capability: encryption-at-rest

### Requirement E-01: AES-256 Encryption for PII

**User Story**: Como seguridad, necesito que datos sensibles (DNI, CBU) se almacenen cifrados en BD.

**Scenario 4.1 — Encrypt plaintext → ciphertext**
```gherkin
Given EncryptionService con clave válida (32 bytes base64)
When llamo encrypt("12345678")
Then retorna un string cifrado (no contiene "12345678")
And longitud > len(plaintext) (overhead de Fernet)
```

**Scenario 4.2 — Decrypt ciphertext → plaintext**
```gherkin
Given EncryptionService
And ciphertext = encrypt("12345678")
When llamo decrypt(ciphertext)
Then retorna "12345678" (round-trip success)
```

**Scenario 4.3 — Encryption key from env**
```gherkin
Given env var ENCRYPTION_KEY="base64-encoded-32-bytes"
When EncryptionService() inicializa sin parámetro
Then lee ENCRYPTION_KEY
And funciona encrypt/decrypt correctamente
```

**Scenario 4.4 — Missing key raises error**
```gherkin
Given ENCRYPTION_KEY no definida
When intento inicializar EncryptionService()
Then lanza ValueError("ENCRYPTION_KEY not set")
```

**Scenario 4.5 — Encrypted field in ORM**
```gherkin
Given DummyEntity con columna email: str
And un property (descriptor) que cifra al asignar
When obj.email = "user@example.com"
Then en memoria, obj.email == "user@example.com" (plaintext)
And en BD, value está cifrado
When obj se reloaded de BD
Then el property lo descifra automáticamente
```

---

## Capability: base-models

### Requirement BM-01: BaseMixin with Audit Timestamps

**User Story**: Como ORM, necesito que toda entidad tenga id, tenant_id, created_at, updated_at, deleted_at automáticamente.

**Scenario 5.1 — Mixin fields exist**
```gherkin
Given clase DummyEntity(BaseModel)
Then tiene atributos: id, tenant_id, created_at, updated_at, deleted_at
And id es UUID PK
And tenant_id es UUID FK (indexed)
And timestamps son datetime
```

**Scenario 5.2 — created_at asignado al INSERT**
```gherkin
Given DummyEntity obj con created_at=None
When se persiste (INSERT)
Then created_at == datetime.utcnow() (auto-set)
```

**Scenario 5.3 — updated_at actualizado al UPDATE**
```gherkin
Given DummyEntity persistido con updated_at=T1
When se actualiza otra columna
Then updated_at > T1 (refresh automático)
```

**Scenario 5.4 — Índices en columnas críticas**
```gherkin
Given schema de BD
When se consulta con explain plan
Then tenant_id usa índice (fast scan)
And deleted_at usa índice (fast soft delete filter)
```

---

## Capability: soft-delete (continued)

### Requirement SD-02: Alembic Migration Setup

**User Story**: Como desarrollador, necesito que la migración 001 cree la tabla tenant con el esquema correcto.

**Scenario 6.1 — Migration 001 creates tenant table**
```gherkin
Given DB vacía
When corro alembic upgrade 001
Then tabla tenant existe con columnas: id, name, domain, created_at, updated_at, deleted_at
And PK en id (UUID)
And índice en domain (unique)
And índice en deleted_at
```

**Scenario 6.2 — Migration rollback drops table**
```gherkin
Given tabla tenant existe (después de upgrade 001)
When corro alembic downgrade -1 (revierte a None)
Then tabla tenant no existe
And DB vuelve a estado inicial (vacío)
```

**Scenario 6.3 — One migration per change convention**
```gherkin
Given C-02 añade Tenant model
And C-03 añade Usuario model
Then C-02 tiene migración 001: tenant
And C-03 tiene migración 002: usuario
And migraciones son secuenciales, nunca intercaladas
```

---

## Integration: Multi-Tenant + Soft Delete

### Scenario 7.1 — Soft delete con tenant scope**
```gherkin
Given obj1 (tenant=t1, active)
And obj2 (tenant=t2, active)
When llamo repo.soft_delete(id=id1, tenant_id=t1)
Then obj1 está soft-deleted
And obj2 sigue activo
And repo.list_all(t1) no incluye obj1
And repo.list_all(t2) incluye obj2
```

---

## Testing Strategy (TDD Strict)

| Scenario | Test File | Layer | Assertion |
|----------|-----------|-------|-----------|
| 1.1 | `test_tenant_model.py` | Unit | Tenant instantiation, fields exist |
| 1.2 | `test_tenant_model.py` | Integration | INSERT → row exists + timestamps |
| 2.1 | `test_repository_tenant_scope.py` | Integration | Multi-tenant isolation (2 tenants, list_all filters correct) |
| 2.2 | `test_repository_tenant_scope.py` | Integration | find_by_id respects tenant boundary |
| 2.3 | `test_repository_tenant_scope.py` | Static | Type checker detects missing tenant_id |
| 3.1 | `test_soft_delete.py` | Unit | BaseMixin has deleted_at field |
| 3.2 | `test_soft_delete.py` | Integration | soft_delete() marks with timestamp |
| 3.3 | `test_soft_delete.py` | Integration | list_all excludes soft-deleted; list_all_including_deleted includes |
| 3.4 | `test_soft_delete.py` | Integration | Admin query includes soft-deleted |
| 3.5 | `test_soft_delete.py` | Integration | find_by_id returns None for soft-deleted |
| 4.1–4.5 | `test_encryption.py` | Unit | encrypt/decrypt round-trip, env key, missing key error, ORM integration |
| 5.1–5.4 | `test_base_mixin.py` | Unit/Integration | Mixin fields, created_at/updated_at auto-set, indexes |
| 6.1–6.3 | `test_alembic_migrations.py` | Integration | Migration 001 creates/drops table, sequential naming |
| 7.1 | `test_integration_soft_delete_multi_tenant.py` | Integration | Soft delete + tenant scope interaction |

---

## Non-Functional Requirements

- **Performance**: Índices en `tenant_id` + `deleted_at` garantizan queries < 100ms en 1M registros
- **Concurrency**: SQLAlchemy async + connection pooling; soft delete uses pessimistic locking si es necesario
- **Test Coverage**: ≥80% líneas, ≥90% reglas de negocio (soft delete, tenant isolation, encryption)
- **Security**: ENCRYPTION_KEY nunca hardcoded; nunca loguear plaintexts; secrets en env/Vault
