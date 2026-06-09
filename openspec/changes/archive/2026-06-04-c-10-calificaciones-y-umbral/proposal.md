# Proposal: c-10-calificaciones-y-umbral

## Problema / Oportunidad

Actualmente el sistema no tiene capacidad de registrar ni analizar calificaciones de alumnos. Los docentes trabajan con datos del LMS fuera de la plataforma, sin poder detectar alumnos en riesgo ni configurar criterios de aprobación. Sin calificaciones ni umbrales, no es posible ejecutar el flujo central de análisis académico (FL-02) ni alimentar los módulos de atrasados, ranking y comunicaciones (C-11, C-12).

## Solución Propuesta

Implementar los modelos `Calificacion` y `UmbralMateria` con su lógica de derivación de `aprobado`, más los endpoints para:
1. Importar calificaciones desde archivo del LMS con detección de columnas numéricas (RN-01) y textuales (RN-02), vista previa y selección de actividades.
2. Importar reporte de finalización (F1.2) para detectar entregas sin corregir.
3. Configurar umbral de aprobación por materia y asignación docente (F2.1, RN-03, defecto 60%).

## Alcance

- [ ] **Incluir**:
  - Modelo `Calificacion` (numérica/textual, `aprobado` derivado, origen Importado/Manual)
  - Modelo `UmbralMateria` (umbral_pct por asignación, valores aprobatorios textuales)
  - Migración Alembic 011 con tablas `calificacion` y `umbral_materia`
  - Servicio de importación con pipeline preview → confirm
  - Endpoints REST para importar calificaciones, importar finalización, configurar umbral
  - Auditoría con código `CALIFICACIONES_IMPORTAR`
  - Tests de derivación de `aprobado`, preview, selección de actividades, umbral por asignación

- [ ] **Excluir**:
  - Cómputo de alumnos atrasados (C-11)
  - Ranking de actividades aprobadas (C-11)
  - Comunicaciones con alumnos (C-12)
  - UI frontend (C-22)
  - Sincronización automática nocturna (infraestructura futura)

## Impacto

- **Backend**: Nuevos modelos, repositorios, servicios y routers en `app/`
- **DB**: Tablas `calificacion` y `umbral_materia` (migración 011)
- **Auditoría**: Nuevo código de evento `CALIFICACIONES_IMPORTAR`
- **Riesgo**: Archivos mal formados del LMS pueden generar errores de parseo
- **Mitigación**: Vista previa obligatoria antes de confirmar importación; validación estricta de columnas esperadas
