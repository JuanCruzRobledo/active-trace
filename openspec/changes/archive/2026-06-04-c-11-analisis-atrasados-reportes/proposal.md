## Why

Con las calificaciones importadas y el umbral configurado (C-10), el sistema necesita transformar esos datos en información accionable para los docentes. Sin esta capa de análisis, las calificaciones son solo datos sin contexto. Este change permite detectar alumnos en riesgo, priorizar correcciones y dar visibilidad del estado académico a cada actor (tutor, profesor, coordinador, admin) según su nivel de alcance.

## What Changes

- **Nuevo módulo de análisis**: endpoints y servicios para cómputo de atrasados, ranking, reportes rápidos, notas finales agrupadas y exportación de TPs sin corregir.
- **Monitores multi-rol**: vista general (coordinación/admin), vista de seguimiento (tutor/profesor) con filtros, y vista extendida con rango de fechas para coordinación/admin.
- NO se crean nuevos modelos de datos — todo el análisis opera sobre los modelos existentes `Calificacion` y `UmbralMateria` (C-10) más las entidades de `Asignacion`, `EntradaPadron` y `Materia` existentes.
- Lógica de cálculo en Services (no en Routers ni SQL disperso).

## Capabilities

### New Capabilities
- `analisis-atrasados`: Cómputo de alumnos atrasados según RN-06 (actividades faltantes o nota < umbral), con filtros por materia, cohorte, comisión y rol del usuario consultante.
- `rankings-reportes`: Ranking de actividades aprobadas (RN-09), reportes rápidos por materia con métricas clave, notas finales agrupadas por alumno, y exportación de TPs sin corregir (RN-07/RN-08).
- `monitores-seguimiento`: Monitor general transversal (coordinación/admin, F2.7) con filtros por materia/regional/comisión/estado; monitor de seguimiento (tutor/profesor, F2.8) filtrado por alumno/correo/comisión/regional/actividad; monitor extendido con rango de fechas (coordinación/admin, F2.9).

### Modified Capabilities
<!-- No existing spec-level requirements change — los specs de calificaciones y umbral no se modifican, se consumen como fuente de datos. -->

## Impact

- **Nuevos routers**: `backend/app/api/v1/routers/analisis.py` — endpoints agrupados bajo `/api/analisis/*`
- **Nuevos services**: `backend/app/services/analisis_service.py` — lógica de cómputo de atrasados, ranking, reportes, monitores
- **Nuevos repositorios**: `backend/app/repositories/analisis_repository.py` — queries de agregación sobre `Calificacion`, `UmbralMateria`, `EntradaPadron`, `Asignacion`
- **Nuevos schemas**: `backend/app/schemas/analisis.py` — DTOs de request/response para cada endpoint
- **Permisos**: guard `atrasados:ver` para acceso a los endpoints de análisis
- **Tests**: tests de integración con base real para cada escenario (atrasados, ranking, monitores, export)
