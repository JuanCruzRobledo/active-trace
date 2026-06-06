## 1. Modelos y Migración

- [x] 1.1 Crear modelo `ProgramaMateria` con campos: id, tenant_id, materia_id, carrera_id, cohorte_id, titulo, referencia_archivo, cargado_at, soft delete mixin (materia_id FK → Materia, carrera_id FK → Carrera, cohorte_id FK → Cohorte)
- [x] 1.2 Crear modelo `FechaAcademica` con campos: id, tenant_id, materia_id, cohorte_id, tipo (enum), numero, periodo, fecha, titulo, soft delete mixin
- [x] 1.3 Agregar enum `TipoFechaAcademica` a `backend/app/models/enums.py`: Parcial, TP, Coloquio, Recuperatorio
- [x] 1.4 Crear migración Alembic 018 con tablas `programa_materia` y `fecha_academica` + índices (tenant_id, materia_id, cohorte_id) + unique constraint `(tenant_id, materia_id, carrera_id, cohorte_id)` en programa_materia y `(tenant_id, materia_id, cohorte_id, tipo, numero)` en fecha_academica
- [x] 1.5 Agregar relaciones SQLAlchemy: ProgramaMateria ↔ Materia/Carrera/Cohorte, FechaAcademica ↔ Materia/Cohorte
- [x] 1.6 Registrar modelos en `backend/app/models/__init__.py`

## 2. Pydantic Schemas

- [x] 2.1 Crear `ProgramaMateriaCreate` (materia_id, carrera_id, cohorte_id, titulo, referencia_archivo)
- [x] 2.2 Crear `ProgramaMateriaResponse` (id, titulo, materia_id, carrera_id, cohorte_id, referencia_archivo, cargado_at)
- [x] 2.3 Crear `ProgramaMateriaListResponse` (items + total)
- [x] 2.4 Crear `FechaAcademicaCreate` (materia_id, cohorte_id, tipo, numero, periodo, fecha, titulo)
- [x] 2.5 Crear `FechaAcademicaUpdate` (todos los campos de create opcionales)
- [x] 2.6 Crear `FechaAcademicaResponse` (id + todos los campos + created_at, updated_at)
- [x] 2.7 Crear `FechaAcademicaListResponse` (items + total)
- [x] 2.8 Crear `LmsExportResponse` (contenido_html como string)
- [x] 2.9 Agregar `ConfigDict(extra='forbid')` en todos los schemas

## 3. Repository

- [x] 3.1 Implementar `ProgramaMateriaRepository` con métodos: create, get_by_id (con tenant scope), list (filtros materia/carrera/cohorte), delete (hard delete con verificación de existencia)
- [x] 3.2 Implementar `FechaAcademicaRepository` con métodos: create, get_by_id (con tenant scope), list (filtros materia/cohorte/tipo/periodo), update, soft_delete
- [x] 3.3 Implementar tenant scope obligatorio en todos los repositorios + unique validation en create

## 4. Service

- [x] 4.1 Implementar `ProgramaService.subir_programa` — validar materia/carrera/cohorte existen en el tenant, validar unicidad, crear programa, audit log `PROGRAMA_SUBIR`
- [x] 4.2 Implementar `ProgramaService.listar_programas` — con filtros combinables, sin paginación inicial
- [x] 4.3 Implementar `ProgramaService.obtener_programa` — obtener detalle con referencia_archivo
- [x] 4.4 Implementar `ProgramaService.eliminar_programa` — hard delete con audit log `PROGRAMA_ELIMINAR`
- [x] 4.5 Implementar `FechaAcademicaService.crear_fecha` — validar materia/cohorte existen, validar unicidad (tipo+numero), audit log `FECHA_ACADEMICA_CREAR`
- [x] 4.6 Implementar `FechaAcademicaService.listar_fechas` — con filtros combinables, ordenadas por fecha ASC
- [x] 4.7 Implementar `FechaAcademicaService.obtener_fecha` — detalle individual
- [x] 4.8 Implementar `FechaAcademicaService.actualizar_fecha` — validar unicidad si cambia tipo/numero, audit log `FECHA_ACADEMICA_MODIFICAR`
- [x] 4.9 Implementar `FechaAcademicaService.eliminar_fecha` — soft delete con audit log `FECHA_ACADEMICA_ELIMINAR`
- [x] 4.10 Implementar `FechaAcademicaService.generar_lms_export` — generar fragmento HTML tabla con fechas de una materia×cohorte

## 5. Router y Endpoints

- [x] 5.1 Crear router `/api/programas` con prefix y tags
- [x] 5.2 Crear endpoint `POST /api/programas` — subir programa, guard `estructura:gestionar`
- [x] 5.3 Crear endpoint `GET /api/programas` — listar programas (con filtros query params)
- [x] 5.4 Crear endpoint `GET /api/programas/{id}` — obtener detalle
- [x] 5.5 Crear endpoint `DELETE /api/programas/{id}` — eliminar programa, guard `estructura:gestionar`
- [x] 5.6 Crear router `/api/fechas-academicas` con prefix y tags
- [x] 5.7 Crear endpoint `POST /api/fechas-academicas` — crear fecha, guard `estructura:gestionar`
- [x] 5.8 Crear endpoint `GET /api/fechas-academicas` — listar fechas (con filtros query params)
- [x] 5.9 Crear endpoint `GET /api/fechas-academicas/{id}` — obtener detalle
- [x] 5.10 Crear endpoint `PATCH /api/fechas-academicas/{id}` — actualizar fecha, guard `estructura:gestionar`
- [x] 5.11 Crear endpoint `DELETE /api/fechas-academicas/{id}` — eliminar fecha (soft delete), guard `estructura:gestionar`
- [x] 5.12 Crear endpoint `GET /api/fechas-academicas/lms-export` — exportar HTML para LMS, guard `estructura:gestionar`
- [x] 5.13 Registrar ambos routers en `app/main.py`

## 6. Tests

- [x] 6.1 Tests de repositorio: CRUD ProgramaMateria, unique constraint materia×carrera×cohorte, filtros, hard delete, aislamiento tenant
- [x] 6.2 Tests de repositorio: CRUD FechaAcademica, unique constraint (materia_id, cohorte_id, tipo, numero), soft delete (no aparece en listados), filtros combinables
- [x] 6.3 Tests de servicio: subir programa, eliminar con audit, obtener detalle, listar con filtros
- [x] 6.4 Tests de servicio: crear fecha con validación de unicidad, actualizar fecha, eliminar (soft delete), export LMS genera HTML válido
- [x] 6.5 Tests de router: endpoints REST con autenticación, permisos (403 en gestionar), flujos felices, 404 en recursos inexistentes, 409 en conflictos de unicidad
- [x] 6.6 Tests de export LMS: verificar que el HTML contiene tabla con las fechas, formato correcto, Content-Type text/plain
- [x] 6.7 Verificar aislamiento multi-tenant en todos los tests (tenant A no ve datos de tenant B)

## 7. Auditoría y Seed

- [x] 7.1 Agregar constantes `ACCION_PROGRAMA_SUBIR`, `ACCION_PROGRAMA_ELIMINAR`, `ACCION_FECHA_ACADEMICA_CREAR`, `ACCION_FECHA_ACADEMICA_MODIFICAR`, `ACCION_FECHA_ACADEMICA_ELIMINAR` a `audit_service.py`
- [x] 7.2 Agregar los nuevos códigos a `VALID_ACCION_CODES` en `audit_service.py`
- [x] 7.3 Verificar que `PERM_ESTRUCTURA_GESTIONAR` ya existe en `permissions.py` y está en `PERMISOS_CATALOGO` — verificar mapeo a roles COORDINADOR y ADMIN en seed script
