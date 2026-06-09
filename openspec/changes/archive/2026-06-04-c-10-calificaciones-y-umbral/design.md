# Design: c-10-calificaciones-y-umbral

## Context

Este change se construye sobre los cimientos ya establecidos:
- **C-07**: `Usuario`, `Asignacion`, `EncryptionService`
- **C-09**: `VersionPadron`, `EntradaPadron`, import xlsx/csv con preview, `MoodleWSClient`

Actualmente el sistema no tiene modelos de calificaciones. Este change introduce la capacidad de importar notas desde el LMS, configurar umbrales de aprobación, y derivar el campo `aprobado` como paso previo al análisis de atrasados (C-11).

## Goals / Non-Goals

**Goals:**
- Modelo `Calificacion` con nota numérica y/o textual, `aprobado` derivado, origen (Importado/Manual), FK a `EntradaPadron` y `Materia`.
- Modelo `UmbralMateria` con umbral_pct y valores_aprobatorios textuales, FK a `Asignacion`.
- Migración Alembic 011 con tablas `calificacion` y `umbral_materia`.
- Importar calificaciones desde archivo LMS (F1.1): detección de columnas numéricas (RN-01) y textuales (RN-02), vista previa, selección de actividades.
- Importar reporte de finalización (F1.2): detectar TPs entregados sin calificación.
- Configurar umbral por materia (F2.1, RN-03, defecto 60%).
- Auditoría con código `CALIFICACIONES_IMPORTAR`.

**Non-Goals:**
- Cómputo de alumnos atrasados (C-11).
- Ranking de actividades aprobadas (C-11).
- Comunicaciones con alumnos (C-12).
- UI frontend (C-22).
- Sincronización nocturna automática.

## Decisions

### D1 — `aprobado` como campo derivado en el modelo, no calculado en demanda

**Decisión**: El campo `aprobado` de `Calificacion` se calcula y persiste al momento de importar/configurar el umbral. No se recalcula en cada consulta.

**Fundamento**: Una vez que se importan calificaciones y se configura el umbral, el resultado de `aprobado` es determinista y no cambia a menos que se modifique el umbral explícitamente. Persistirlo evita recalcular en cada lectura y simplifica las queries de C-11 (atrasados). Si el usuario cambia el umbral, se recalculan en lote las calificaciones afectadas.

**Alternativa rechazada**: Calcular `aprobado` como propiedad transient/SQL expression. Se descarta porque las queries de C-11 (atrasados, ranking) serían más complejas y lentas al tener que recalcular en cada acceso.

### D2 — Pipeline de importación en dos pasos (preview → confirm), mismo patrón que C-09

**Decisión**: El endpoint `POST /api/calificaciones/importar` acepta el archivo, lo parsea, detecta columnas (numéricas por sufijo `(Real)` según RN-01, textuales por catálogo configurable), y devuelve vista previa con actividades detectadas y cantidad de filas. El usuario confirma con un segundo llamado que incluye un `preview_token`. El pipeline de preview es exactamente el mismo patrón implementado en C-09 (padrón).

**Fundamento**: Consistencia con C-09. Preview obligatorio evita importaciones accidentales.

**Formatos aceptados**: `.xlsx` (openpyxl) y `.csv` (csv estándar).

### D3 — Umbral configurable por asignación, no global

**Decisión**: `UmbralMateria` se relaciona con `Asignacion` (docente × materia × cohorte). Cada docente puede tener su propio umbral para la misma materia. Si no existe configuración, se usa el valor por defecto del tenant (60%).

**Fundamento**: La regla RN-03 explicita que el umbral es "configurable por docente por materia". Modelarlo contra `Asignacion` respeta esa semántica. Un cambio de umbral gatilla el recálculo en lote de `aprobado` para todas las `Calificacion` de esa asignación.

### D4 — Detección de columnas por sufijo `(Real)` (RN-01) + catálogo textual (RN-02)

**Decisión**: Al parsear el archivo de calificaciones, las columnas cuyo encabezado termina en `(Real)` se interpretan como nota numérica. Las columnas con valores textuales conocidos ("Satisfactorio", "Supera lo esperado", etc.) se detectan por contenido. La lista de valores textuales aprobatorios es configurable en `UmbralMateria.valores_aprobatorios`.

**Fundamento**: RN-01 y RN-02 definen explícitamente estas reglas de detección. El sufijo `(Real)` es el contrato con el LMS.

### D5 — Reporte de finalización cruza con calificaciones importadas

**Decisión**: `POST /api/calificaciones/finalizacion` acepta un archivo de finalización del LMS. El servicio cruza cada entrada contra las `Calificacion` existentes (por `entrada_padron_id` + actividad). Las actividades finalizadas por el alumno pero sin calificación registrada se listan como "posibles entregas sin corregir". Solo aplica a actividades de escala textual (RN-08).

**Fundamento**: RN-07 y RN-08 definen exactamente este cruce y filtro.

## Modelo de Datos

### Entidad: Calificacion

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID | PK |
| `tenant_id` | UUID | FK → Tenant |
| `entrada_padron_id` | UUID | FK → EntradaPadron (alumno) |
| `materia_id` | UUID | FK → Materia |
| `actividad` | texto | Nombre de la actividad evaluable |
| `nota_numerica` | decimal | Valor numérico (nulo si textual) |
| `nota_textual` | texto | Descripción cualitativa |
| `aprobado` | booleano | Derivado: numérica ≥ umbral O textual ∈ valores_aprobatorios |
| `origen` | enum | Importado \| Manual |
| `importado_at` | datetime | Timestamp de importación |
| `created_at` | datetime | Heredado de BaseMixin |
| `updated_at` | datetime | Heredado de BaseMixin |

### Entidad: UmbralMateria

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID | PK |
| `tenant_id` | UUID | FK → Tenant |
| `asignacion_id` | UUID | FK → Asignacion (docente × materia × cohorte) |
| `materia_id` | UUID | FK → Materia |
| `umbral_pct` | entero | Porcentaje mínimo de aprobación (defecto: 60) |
| `valores_aprobatorios` | JSONB | Lista de valores textuales que cuentan como aprobado |
| `created_at` | datetime | Heredado de BaseMixin |
| `updated_at` | datetime | Heredado de BaseMixin |

### Relaciones

```
EntradaPadron (1) ── (N) Calificacion
Materia (1) ── (N) Calificacion
Materia (1) ── (N) UmbralMateria
Asignacion (1) ── (N) UmbralMateria (único por asignación en la práctica)
```

### Índices

- `calificacion`: índice compuesto `(entrada_padron_id, materia_id, actividad)` para cruce rápido con reporte de finalización
- `calificacion`: índice `(materia_id)` para filtros por materia
- `umbral_materia`: unique index `(asignacion_id, materia_id)` con `WHERE deleted_at IS NULL` (soft-delete)
- Todos los modelos heredan `tenant_id` indexado por `BaseMixin`

## APIs

### POST /api/calificaciones/importar/preview
- **Input**: Archivo `.xlsx`/`.csv` (multipart), `materia_id`
- **Output**: `{ actividades_detectadas: [...], filas: N, preview_token: "hash" }`
- **Auth**: `calificaciones:importar` (PROFESOR sobre sus materias, COORDINADOR global)
- **Errors**: 400 (archivo inválido), 422 (validación)

### POST /api/calificaciones/importar/confirm
- **Input**: `{ preview_token, materia_id, actividades_seleccionadas: [...] }`
- **Output**: `{ calificaciones_importadas: N, actividad: { nombre, count } }`
- **Auth**: `calificaciones:importar`
- **Errors**: 400 (preview_token inválido/expirado), 409 (archivo modificado)
- **Efecto**: Persiste calificaciones, deriva `aprobado`, genera audit `CALIFICACIONES_IMPORTAR`

### POST /api/calificaciones/finalizacion
- **Input**: Archivo de finalización (multipart), `materia_id`
- **Output**: `{ posibles_sin_corregir: [{ alumno, actividad, entregado_en }] }`
- **Auth**: `calificaciones:importar`
- **Errors**: 400 (archivo inválido)
- **Reglas**: Solo actividades textuales (RN-08); cruce contra calificaciones existentes

### GET /api/calificaciones/umbral
- **Query**: `materia_id` (opcional), `asignacion_id` (opcional)
- **Output**: Configuración de umbral actual (o default del tenant si no existe)
- **Auth**: `calificaciones:importar`
- **Scope**: PROFESOR solo ve su propia asignación; COORDINADOR/ADMIN ven todo

### PUT /api/calificaciones/umbral
- **Input**: `{ materia_id, asignacion_id, umbral_pct?, valores_aprobatorios? }`
- **Output**: `UmbralMateria` actualizado
- **Auth**: `calificaciones:importar`
- **Efecto**: Actualiza umbral; si cambia `umbral_pct` o `valores_aprobatorios`, gatilla recálculo en lote de `aprobado` para calificaciones de esa asignación
- **Errors**: 422 (umbral_pct fuera de rango 0-100)

## Seguridad

- Todos los endpoints requieren permiso `calificaciones:importar`
- PROFESOR: scope automático a sus propias asignaciones (resuelto desde JWT)
- COORDINADOR/ADMIN: scope global sobre cualquier materia del tenant
- Auditoría `CALIFICACIONES_IMPORTAR` en cada importación y cambio de umbral
- Multi-tenancy row-level por `tenant_id` en todos los queries

## Risks / Trade-offs

- **[Riesgo] Archivos LMS mal formados**: usuarios pueden subir archivos con estructura inesperada (columnas faltantes, datos corruptos). **Mitigación**: validación estricta en preview, errores descriptivos.
- **[Riesgo] Preview_token expirado**: si el usuario tarda demasiado entre preview y confirm, el contenido del archivo puede haber cambiado. **Mitigación**: el preview_token incluye hash del contenido completo; si cambia, el confirm rechaza con 409.
- **[Riesgo] Recálculo en lote al cambiar umbral**: si hay muchas calificaciones, el recálculo puede ser lento. **Mitigación**: operación asíncrona con background task si supera N calificaciones (configurable).
- **[Trade-off] `aprobado` persistido**: gana velocidad de consulta a costa de tener que recalcular al cambiar umbral. **Aceptado**: el cambio de umbral es poco frecuente comparado con las lecturas.
