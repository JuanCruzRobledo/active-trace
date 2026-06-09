# Tasks: c-10-calificaciones-y-umbral

## Implementation Checklist

### Grupo 1: Modelos y Migración

- [x] 1.1 Crear modelo `Calificacion` en `backend/app/models/calificacion.py`
  - Campos: id, tenant_id, entrada_padron_id, materia_id, actividad, nota_numerica, nota_textual, aprobado, origen (enum Importado|Manual), importado_at, created_at, updated_at
  - `aprobado` como columna Boolean persistida (no transient — ver D1 del design)
  - FK a `EntradaPadron` y `Materia`
  - Validación: al menos nota_numerica o nota_textual no nulo
  - Origen: enum con valores `Importado` y `Manual`

- [x] 1.2 Crear modelo `UmbralMateria` en `backend/app/models/umbral_materia.py`
  - Campos: id, tenant_id, asignacion_id, materia_id, umbral_pct (default 60), valores_aprobatorios (JSONB), created_at, updated_at
  - Unique index parcial `(asignacion_id, materia_id)` WHERE `deleted_at IS NULL`
  - FK a `Asignacion` y `Materia`

- [x] 1.3 Crear enum `OrigenCalificacion` en `backend/app/models/enums.py` (o inline en el modelo)
  - Valores: `Importado`, `Manual`

- [x] 1.4 Crear migración Alembic 011 con tablas `calificacion` y `umbral_materia`
  - Índices compuestos: `(entrada_padron_id, materia_id, actividad)` en calificacion
  - Índice `(materia_id)` en calificacion
  - Partial unique index en umbral_materia
  - FK con ON DELETE CASCADE apropiado

### Grupo 2: Repositories

- [x] 2.1 Crear `CalificacionRepository` en `backend/app/repositories/calificacion_repository.py`
  - Hereda de `BaseRepository[Calificacion]`
  - `list_by_materia(materia_id) → list[Calificacion]`
  - `list_by_entrada_padron(entrada_padron_id) → list[Calificacion]`
  - `find_by_actividad(materia_id, actividad) → list[Calificacion]`
  - `bulk_create(calificaciones: list[Calificacion]) → list[Calificacion]`
  - `delete_by_materia(materia_id)` — soft-delete lógico (scope tenant)
  - `recalcular_aprobado(asignacion_id, umbral_pct, valores_aprobatorios)` — UPDATE batch

- [x] 2.2 Crear `UmbralMateriaRepository` en `backend/app/repositories/umbral_materia_repository.py`
  - Hereda de `BaseRepository[UmbralMateria]`
  - `find_by_asignacion(asignacion_id) → UmbralMateria | None`
  - `find_by_materia(materia_id) → list[UmbralMateria]`
  - `upsert(asignacion_id, materia_id, umbral_pct, valores_aprobatorios) → UmbralMateria`

### Grupo 3: Services

- [x] 3.1 Crear `CalificacionService` en `backend/app/services/calificacion_service.py`
  - `importar_preview(archivo, materia_id, usuario) → PreviewResult`
    - Parsear archivo (xlsx/csv), detectar columnas numéricas (sufijo `(Real)` — RN-01) y textuales (RN-02)
    - Detectar alumnos por `EntradaPadron` activa para esa materia×cohorte
    - Retornar preview con actividades detectadas, cantidad de filas, preview_token (hash del contenido)
  - `importar_confirm(preview_token, materia_id, actividades_seleccionadas, usuario) → ImportResult`
    - Validar preview_token contra el hash del archivo original
    - Persistir calificaciones, derivar `aprobado` según umbral actual (o default 60%)
    - Generar audit `CALIFICACIONES_IMPORTAR`
  - `procesar_finalizacion(archivo, materia_id, usuario) → FinalizacionResult`
    - Parsear archivo de finalización
    - Cruzar contra calificaciones existentes por `(entrada_padron_id, actividad)`
    - Listar solo actividades textuales sin calificación (RN-07, RN-08)
    - Retornar tabla de "posibles entregas sin corregir"

- [x] 3.2 Crear `UmbralService` en `backend/app/services/umbral_service.py`
  - `obtener_umbral(materia_id, asignacion_id) → UmbralMateria | dict` (default del tenant si no existe)
  - `configurar_umbral(materia_id, asignacion_id, umbral_pct, valores_aprobatorios, usuario) → UmbralMateria`
    - Si cambia umbral_pct o valores_aprobatorios → gatilla recálculo en lote de `aprobado`
  - `_recalcular_en_lote(asignacion_id, umbral_pct, valores_aprobatorios)` — método interno
  - Scope: PROFESOR solo sobre su asignación; COORDINADOR/ADMIN global

### Grupo 4: Router y Endpoints

- [x] 4.1 Crear router `calificaciones` en `backend/app/api/v1/routers/calificaciones.py`
  - Prefix: `/api/calificaciones`
  - Tags: `Calificaciones`
  - Guard: `require_permission("calificaciones:importar")`
  - Scope implícito: PROFESOR filtra por sus asignaciones; COORDINADOR/ADMIN pasa query param

- [x] 4.2 Endpoint `POST /api/calificaciones/importar/preview`
  - DTO request: `archivo: UploadFile, materia_id: UUID`
  - DTO response: `{ actividades_detectadas: list[str], filas: int, preview_token: str }`

- [x] 4.3 Endpoint `POST /api/calificaciones/importar/confirm`
  - DTO request: `{ preview_token: str, materia_id: UUID, actividades_seleccionadas: list[str] }`
  - DTO response: `{ calificaciones_importadas: int, actividades: list[{nombre, count}] }`

- [x] 4.4 Endpoint `POST /api/calificaciones/finalizacion`
  - DTO request: `archivo: UploadFile, materia_id: UUID`
  - DTO response: `{ posibles_sin_corregir: list[{ alumno_nombre, actividad, entregado_en }] }`

- [x] 4.5 Endpoint `GET /api/calificaciones/umbral`
  - Query params: `materia_id` (opcional), `asignacion_id` (opcional)
  - DTO response: `{ umbral_pct: int, valores_aprobatorios: list[str] }`
  - Si no existe configuración, retorna default del tenant

- [x] 4.6 Endpoint `PUT /api/calificaciones/umbral`
  - DTO request: `{ materia_id: UUID, asignacion_id: UUID, umbral_pct?: int, valores_aprobatorios?: list[str] }`
  - DTO response: `UmbralMateria`
  - Efecto: recálculo en lote de `aprobado` si cambia configuración

- [x] 4.7 Registrar router en `backend/app/api/v1/api.py`

### Grupo 5: Tests

- [x] 5.1 Test: Derivación de `aprobado` — nota numérica ≥ umbral
  - Fixture: Calificacion con nota_numerica=75, umbral_pct=60 → aprobado=True
  - Fixture: Calificacion con nota_numerica=40, umbral_pct=60 → aprobado=False
  - Fixture: Calificacion con nota_numerica=60, umbral_pct=60 → aprobado=True (borde exacto)

- [x] 5.2 Test: Derivación de `aprobado` — nota textual vs conjunto aprobatorio
  - Fixture: nota_textual="Satisfactorio", valores_aprobatorios=["Satisfactorio", "Supera lo esperado"] → aprobado=True
  - Fixture: nota_textual="No satisfactorio", mismos valores → aprobado=False
  - Fixture: nota_textual="Supera lo esperado" → aprobado=True

- [x] 5.3 Test: Derivación con nota numérica y textual simultáneas
  - Si ambas presentes, numérica tiene prioridad (se compara contra umbral_pct)

- [x] 5.4 Test: Import preview — detección de columnas numéricas (RN-01)
  - Archivo con columna "Parcial (Real)" → se detecta como numérica
  - Archivo con columna "TP Final" → no se detecta como numérica

- [x] 5.5 Test: Import preview — detección de columnas textuales (RN-02)
  - Archivo con columna "Desempeño" y valores "Satisfactorio" → se detecta como textual

- [x] 5.6 Test: Import preview → confirm ciclo completo
  - Subir archivo → preview → confirm con actividades seleccionadas
  - Verificar que se persisten solo las actividades seleccionadas
  - Verificar que `aprobado` se deriva correctamente

- [x] 5.7 Test: Preview_token inválido → confirm rechaza con 400
  - Preview_token que no coincide con hash del archivo

- [x] 5.8 Test: Reporte de finalización — detección de entregas sin calificar
  - Archivo de finalización con alumnos que tienen actividades finalizadas
  - Solo actividades textuales aparecen en la lista (RN-08)
  - Actividades ya calificadas NO aparecen

- [x] 5.9 Test: Configurar umbral — creación y actualización
  - Crear umbral con umbral_pct=75 → se persiste y retorna
  - Actualizar umbral_pct → se actualiza y recalcula aprobado
  - Umbral con valores_aprobatorios personalizados

- [x] 5.10 Test: Umbral por asignación no afecta a otros docentes (RN-03)
  - Dos asignaciones distintas para la misma materia
  - Cambiar umbral de una no afecta a la otra

- [x] 5.11 Test: Scope — PROFESOR solo ve/modifica sus propias asignaciones
  - PROFESOR intenta configurar umbral de otra asignación → 403

- [x] 5.12 Test: Auditoría `CALIFICACIONES_IMPORTAR` se genera en importación y cambio de umbral

- [x] 5.13 Test: Aislamiento multi-tenant — datos de tenant A no visibles en tenant B

## Dependencias

- **C-07**: Modelos `Asignacion`, `Usuario` para FK y scope docente
- **C-09**: Modelo `EntradaPadron` para FK y cruce de alumno por materia×cohorte
- **Knowledge base**: `04_modelo_de_datos.md` §E7, §E8, `06_funcionalidades.md` F1.1, F1.2, F2.1, `07_flujos_principales.md` FL-02 (pasos 3–5)

## Notas de Implementación

- El campo `aprobado` se persiste (no es transient) — ver D1 del design
- Usar `openpyxl` para xlsx y módulo `csv` estándar para csv (mismo approach que C-09)
- El preview_token es un SHA-256 del contenido completo del archivo
- El recálculo en lote al cambiar umbral debe ejecutarse en la misma transacción que la actualización del umbral
- Seguir las reglas duras del proyecto: snake_case, Pydantic `extra='forbid'`, soft-delete, ≤500 LOC por archivo
- Strict TDD: test que falla → código mínimo → triangulación → refactor
