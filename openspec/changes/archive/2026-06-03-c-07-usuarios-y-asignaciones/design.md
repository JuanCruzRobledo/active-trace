## Context

Este change se construye sobre los cimientos ya establecidos:
- **C-02**: `Tenant`, `BaseMixin` multi-tenant, `EncryptionService` (AES-256), `BaseRepository[T]`.
- **C-03**: Autenticación JWT, dependencia `get_current_user`.
- **C-04**: RBAC fino, `require_permission("equipos:asignar")`, matriz rol × permiso.
- **C-06**: Modelos `Carrera`, `Cohorte`, `Materia` con partial unique indexes para soft-delete.

Actualmente el sistema no tiene una entidad `Usuario` —existe solo el modelo de `User` del módulo auth (C-03)— ni un mecanismo para asignar roles a personas dentro de contextos académicos. Este change agrega la identidad base del dominio y su vinculo con roles y contextos.

## Goals / Non-Goals

**Goals:**
- Modelo `Usuario` con PII cifrada en reposo, soft-delete y unicidad `(tenant_id, email)`.
- Modelo `Asignacion` vinculando Usuario ↔ Rol ↔ contexto académico (materia/carrera/cohorte), con vigencia temporal, jerarquía via `responsable_id` y soft-delete.
- Endpoints ABM para usuarios (ADMIN) y CRUD para asignaciones (permiso `equipos:asignar`).
- Migración Alembic 005 con tablas `usuario` y `asignacion`.
- Tests que cubran PII cifrada, unicidad, vigencia y multi-rol.

**Non-Goals:**
- Portal de alumnos / perfil de usuario (será en change separado).
- Importación masiva de usuarios desde CSV/Moodle (futuro).
- Clonado de asignaciones entre períodos (C-07 no incluye F4.5).
- Exposición de endpoints públicos para usuarios (solo ADMIN y equipos:asignar).

## Decisions

### 1. Modelos separados de los del módulo auth
- **Decisión**: El `Usuario` del dominio (este change) es un modelo distinto del `User` de autenticación (C-03). Se relacionan 1:1 por `auth_user_id`.
- **Rationale**: El modelo de auth tiene responsabilidades distintas (hash de password, 2FA, refresh tokens) y una tasa de cambio diferente. Separarlos evita acoplar el dominio a detalles de autenticación. El `Usuario` es la entidad de negocio; el `User` auth es la credencial. Ver `docs/ARQUITECTURA.md` §3 (Clean Architecture) — las capas no deben mezclarse.
- **Alternativa considerada**: Extender el `User` de auth con campos del dominio. Se descartó porque mezcla lógica de seguridad con lógica de negocio y rompe la separación de capas.

### 2. Partial unique index para soft-delete (mismo patrón que C-06)
- **Decisión**: El índice único `(tenant_id, email)` filtra `WHERE deleted_at IS NULL`.
- **Rationale**: Sigue exactamente el patrón implementado en C-06 (estructura académica). Permite re-uso del email tras soft-delete sin romper unicidad. Consistente con la regla de "soft-delete siempre" del proyecto.
- **Alternativa considerada**: Unique constraint sin filtro + UNLOGGED table para re-uso. Descartado por ser inconsistente con el patrón ya establecido.

### 3. Encrypted fields con EncryptionService existente (C-02)
- **Decisión**: Los campos PII (email, dni, cuil, cbu, alias_cbu) se cifran en el setter del modelo y se descifran en un getter controlado, usando `EncryptionService` que ya aporta C-02.
- **Rationale**: El servicio de cifrado ya existe y está probado. Aplicar cifrado a nivel de modelo (en los setters/getters de SQLAlchemy) garantiza que ningún código que acceda al modelo obtenga texto plano sin pasar por el descifrado explícito.
- **Alternativa considerada**: Cifrar/descifrar en el repository. Descartado porque requiere que cada método del repository recuerde hacerlo, propenso a fugas. A nivel de modelo es automático y no se puede omitir.

### 4. Asignacion con estado_vigencia derivado
- **Decisión**: `estado_vigencia` NO se almacena en DB; se calcula en tiempo real comparando las fechas `desde`/`hasta` con la fecha actual.
- **Rationale**: Un campo derivado almacenado requeriría sincronización (trigger o actualización periódica). Al ser una función pura de las fechas, calcularlo en tiempo de consulta es determinista y no tiene costo de mantenimiento. Ver KB §3, §5 (vigencia temporal).
- **Alternativa considerada**: Campo almacenado actualizado por trigger. Descartado por complejidad innecesaria.

### 5. Endpoints separated by permission level
- **Decisión**: `/api/admin/usuarios` para ABM de usuarios (solo ADMIN) y `/api/asignaciones` para CRUD de asignaciones (permiso `equipos:asignar`).
- **Rationale**: La gestión de usuarios (crear personas en el sistema) es una operación sensible que debe estar restringida a ADMIN. Las asignaciones (vincular roles a contextos) puede ser operada por COORDINADOR, que tiene el permiso `equipos:asignar`. Esta separación refleja la matriz de la KB §3.3.

### 6. Relación Usuario ↔ Auth User
- **Decisión**: Vía FK `auth_user_id` en `Usuario` apuntando al `User` del módulo auth. Se crea automáticamente un `User` de auth al crear un `Usuario`, usando el email como username inicial y generando una contraseña temporal.
- **Rationale**: Un usuario del sistema debe poder autenticarse. Al crear un `Usuario` (docente/coordinador/etc.) se necesita una cuenta de acceso. Acoplar la creación en un solo paso evita estados inconsistentes (usuario sin cuenta de acceso).
- **Nota**: El ALUMNO se crea desde padrón (E6, change futuro) con flujo distinto.

## Risks / Trade-offs

| Riesgo | Mitigación |
|--------|-----------|
| **Fuga de PII en logs por descuido**: Un desarrollador podría loguear un objeto Usuario completo sin filtrar campos cifrados. | Configurar filtro de logs que enmascare campos PII a nivel de serializer/logging middleware. Tests específicos que verifiquen que no hay PII en texto plano en respuestas. |
| **Performance de descifrado en listados**: Si se listan muchos usuarios, descifrar campos PII para cada uno puede ser lento. | Los campos PII se descifran solo cuando se incluyen en la respuesta; en listados paginados se pueden excluir o enmascarar sin descifrar. |
| **Inconsistencia Usuario ↔ Auth User**: Si falla la creación del auth User después de crear el Usuario, queda un usuario sin acceso. | Usar transacción (Unit of Work): crear ambos dentro de la misma transacción; si falla cualquiera, rollback completo. |
| **Partial unique index no soportado en algunos motores de base de datos**: PostgreSQL lo soporta, pero es específico de motor. | El proyecto ya usa PostgreSQL como BD objetivo. Documentado en ADR-002. |

## Migration Plan

1. **Generar migración Alembic 005** con:
   - Tabla `usuario` (tenant_id, auth_user_id, nombre, apellidos, email_cifrado, dni_cifrado, cuil_cifrado, cbu_cifrado, alias_cbu_cifrado, banco, regional, legajo, legajo_profesional, facturador, estado, soft-delete columns, timestamps).
   - Partial unique index `uq_usuario_email_tenant` ON usuario(tenant_id, email_cifrado) WHERE deleted_at IS NULL.
   - Tabla `asignacion` (tenant_id, usuario_id, rol, materia_id, carrera_id, cohorte_id, comisiones, responsable_id, desde, hasta, soft-delete columns, timestamps).
   - Foreign keys y partial unique index para evitar duplicados activos.
2. **Rollback**: `downgrade` elimina ambas tablas e índices.
3. **Deploy**: Sin cambios breaking (no existían estas tablas antes).
