## 1. Modelos y Migración

- [x] 1.1 Crear modelo `VersionPadron` con campos: id (UUID), tenant_id, materia_id, cohorte_id, cargado_por (FK → Usuario), cargado_at, activa (boolean). Única activa por (materia_id, cohorte_id).
- [x] 1.2 Crear modelo `EntradaPadron` con campos: id (UUID), version_id (FK → VersionPadron), tenant_id, usuario_id (FK → Usuario, nullable), nombre, apellidos, email (cifrado), comision, regional.
- [x] 1.3 Crear migración Alembic con `version_padron` y `entrada_padron`, incluyendo índices y FK.
- [x] 1.4 Crear repositorios `VersionPadronRepository` y `EntradaPadronRepository` con scope de tenant por defecto.

## 2. Integración Moodle Web Services

- [x] 2.1 Crear `integrations/moodle_ws.py` con clase `MoodleWSClient` que recibe URL + token por tenant.
- [x] 2.2 Implementar método `sync_padron(materia_id, cohorte_id)` que consulta participantes del curso y retorna lista normalizada.
- [x] 2.3 Implementar reintentos con backoff exponencial (3 reintentos: 1s, 2s, 4s) para errores transitorios.
- [x] 2.4 Mapear errores de Moodle WS a HTTP 502 con metadata descriptiva.
- [x] 2.5 Escribir tests unitarios del cliente WS con mock de respuestas HTTP.

## 3. Servicio de Padrón

- [x] 3.1 Crear `services/padron_service.py` con lógica de: crear versión, desactivar versión anterior, asociar entradas.
- [x] 3.2 Implementar matching de `EntradaPadron.usuario_id` por email contra usuarios existentes del tenant.
- [x] 3.3 Implementar preview de importación: parseo de xlsx (openpyxl) y csv (csv stdlib), detección de columnas, generación de preview_token.
- [x] 3.4 Implementar confirmación de importación: recibe preview_token, persiste VersionPadron + Entradas.
- [x] 3.5 Implementar lógica de vaciar materia: desactiva versiones activas, limpia datos, registra auditoría (RN-04).
- [x] 3.6 Escribir tests unitarios del servicio (importación, versionado, matching por email, vaciado).

## 4. Endpoints REST y Router

- [x] 4.1 Crear `routers/padron.py` con prefix `/api/padron` y guard `padron:importar`.
- [x] 4.2 Implementar `POST /api/padron/importar` (multipart: file) → preview (primer llamado con `?preview=true`) o confirm (segundo llamado con preview_token).
- [x] 4.3 Implementar `GET /api/padron/{materia_id}/{cohorte_id}` → padrón activo con sus entradas.
- [x] 4.4 Implementar `DELETE /api/padron/{materia_id}/vaciar` → desactiva versiones + limpia datos.
- [x] 4.5 Registrar routers en la aplicación FastAPI.
- [x] 4.6 Escribir tests de integración de endpoints con httpx (cliente de test).

## 5. Permisos y Auditoría

- [x] 5.1 Agregar permiso `padron:importar` al catálogo de permisos (seed data).
- [x] 5.2 Asignar permiso a roles: PROFESOR `(propio)`, COORDINADOR y ADMIN (scope global).
- [x] 5.3 Registrar auditoría con código `PADRON_CARGAR` en cada importación exitosa.
- [x] 5.4 Registrar auditoría con código `PADRON_VACIAR` en cada vaciado exitoso.
- [x] 5.5 Verificar que el guard `padron:importar` protege todos los endpoints del router.

## 6. Tests de Reglas de Negocio

- [x] 6.1 Test: versionado (activar nueva versión desactiva la anterior).
- [x] 6.2 Test: import xlsx con preview + confirm.
- [x] 6.3 Test: import csv con preview + confirm.
- [x] 6.4 Test: entrada sin usuario_id (alumno sin cuenta) se crea correctamente.
- [x] 6.5 Test: matching de usuario_id por email en la importación.
- [x] 6.6 Test: aislamiento multi-tenant (un tenant no ve datos de otro).
- [x] 6.7 Test: vaciar materia no afecta otras materias.
- [x] 6.8 Test: mock de Moodle WS con fallback a importación manual.
- [x] 6.9 Test: 403 si el usuario no tiene permiso `padron:importar`.

## 7. Post-Implementación y Cierre

- [x] 7.1 Ejecutar verify contra specs (confirmar que todos los requirements y scenarios están cubiertos).
- [x] 7.2 Listar tests manuales en el chat para validación humana.
- [x] 7.3 Luego de tests manuales exitosos: actualizar Engram manifest.json vía Engram Sync Import.
- [x] 7.4 Ejecutar `/opsx:archive` para cerrar el change.
