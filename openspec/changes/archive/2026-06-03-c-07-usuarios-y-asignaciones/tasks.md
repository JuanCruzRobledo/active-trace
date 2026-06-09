## 1. Migración y Modelos

- [x] 1.1 Crear migración Alembic 009 para tablas `usuario` y `asignacion` con partial unique indexes para soft-delete
- [x] 1.2 Implementar modelo SQLAlchemy `Usuario` con `tenant_id`, `auth_user_id` (FK → auth.User), PII cifrada (email, dni, cuil, cbu, alias_cbu mediante `EncryptionService`), `banco`, `regional`, `legajo`, `legajo_profesional`, `facturador`, `estado` y soft-delete columns
- [x] 1.3 Implementar modelo SQLAlchemy `Asignacion` con `tenant_id`, `usuario_id` (FK → Usuario), `rol` (enum), `materia_id`/`carrera_id`/`cohorte_id` (FKs opcionales → estructura académica), `comisiones` (lista), `responsable_id` (FK → Usuario, nullable), `desde`, `hasta` y soft-delete columns
- [x] 1.4 Escribir tests unitarios para creación y constraints de unicidad de `Usuario` (tenant_id, email) y `Asignacion`

## 2. Schemas y Repositories

- [x] 2.1 Definir esquemas Pydantic para `Usuario` (Create, Update, Response, List) con `extra='forbid'`, PII enmascarada en Response, y conversión de fechas para soft-delete
- [x] 2.2 Definir esquemas Pydantic para `Asignacion` (Create, Update, Response, List) con `extra='forbid'` y validación de vigencia (desde ≤ hasta)
- [x] 2.3 Implementar `UsuarioRepository` extendiendo `BaseRepository[Usuario]` con métodos `find_by_email(tenant_id, email)`, `list_by_tenant()` con filtros, y `soft_delete()`
- [x] 2.4 Implementar `AsignacionRepository` extendiendo `BaseRepository[Asignacion]` con métodos `list_by_context()`, `list_by_usuario()`, `find_vigentes()`, y `soft_delete()`
- [x] 2.5 Escribir tests de integración para ambos repositories verificando filtrado por tenant_id y soft-delete

## 3. Services (Lógica de Negocio)

- [x] 3.1 Implementar `UsuarioService.create()` con cifrado de PII vía `EncryptionService`, creación de `User` de auth con password temporal, validación de unicidad de email por tenant, y rollback transaccional
- [x] 3.2 Implementar `UsuarioService.update()` y `soft_delete()` con recifrado y re-uso de email permitido tras soft-delete
- [x] 3.3 Implementar `AsignacionService.create()` con validación de existencia de Usuario y contexto académico, y cálculo de estado_vigencia derivado
- [x] 3.4 Implementar `AsignacionService.update()` con extensión de vigencia y recálculo de estado_vigencia
- [x] 3.5 Implementar `AsignacionService.soft_delete()` preservando histórico
- [x] 3.6 Escribir tests de integración para services: unicidad email por tenant, soft-delete con re-uso de email, vigencia (asignación vencida detectada), multi-rol simultáneo, jerarquía responsable

## 4. Routers y Endpoints

- [x] 4.1 Implementar router `/api/admin/usuarios` con endpoints CRUD protegidos por `require_permission("admin:gestionar-usuarios")` (ADMIN)
- [x] 4.2 Asegurar que respuestas de `/api/admin/usuarios` enmascaren PII (email, dni, cuil, cbu, alias_cbu) y que logs no expongan datos sensibles
- [x] 4.3 Implementar router `/api/asignaciones` con endpoints CRUD protegidos por `require_permission("equipos:asignar")` (COORDINADOR, ADMIN)
- [x] 4.4 Verificar que asignaciones vencidas no otorguen acceso (test `test_asignacion_vencida_tiene_estado_vencida` + vigencia en response)
- [x] 4.5 Conectar ambos routers a la app principal y escribir tests E2E de API validando status 201, 400, 409 (unicidad), 403 (RBAC) y PII enmascarada

## 5. Tests de Seguridad y Cumplimiento

- [x] 5.1 Escribir test que verifique que campos PII (email, dni, cuil, cbu, alias_cbu) no aparecen en texto plano en respuestas HTTP
- [x] 5.2 Escribir test que verifique que logs de aplicación no contienen PII en texto plano (usando `caplog` de pytest)
- [x] 5.3 Escribir test de aislamiento multi-tenant para usuario: usuario del tenant A no puede leer/escribir usuarios del tenant B
- [x] 5.4 Escribir test de vigencia: asignación con `hasta < today` no autoriza acceso a recursos protegidos
- [x] 5.5 Escribir test de jerarquía: asignación con `responsable_id` se persiste y puede consultarse
