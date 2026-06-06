## Why

Los docentes y coordinadores necesitan gestionar el ciclo completo de evaluaciones orales (coloquios): convocar alumnos, administrar turnos con cupo, registrar resultados y dar visibilidad del estado a cada actor. Actualmente no existe un módulo centralizado — la coordinación se hace por canales informales. Este change implementa el subsistema de coloquios para cubrir Épica 7 del roadmap.

## What Changes

- Nuevos modelos `Evaluacion`, `ReservaEvaluacion` y `ResultadoEvaluacion` con su migración Alembic.
- API REST para gestionar convocatorias de coloquio: crear, listar, editar, cerrar.
- Importación de padrón de alumnos habilitados por convocatoria.
- Sistema de reserva de turnos por alumno con control de cupo.
- Panel de métricas por convocatoria (convocados, reservas, cupos libres, notas registradas).
- Agenda consolidada de reservas para COORDINADOR/ADMIN.
- Registro académico de resultados con notas finales.
- RBAC con permisos `coloquios:gestionar`, `coloquios:reservar` y `coloquios:ver`.

## Capabilities

### New Capabilities
- `coloquios`: Gestión de convocatorias de coloquio, importación de alumnos, reserva de turnos, registro de resultados y panel de métricas.

### Modified Capabilities
- *(ninguna — no se modifican capacidades existentes)*

## Impact

- **Modelos nuevos**: `Evaluacion`, `ReservaEvaluacion`, `ResultadoEvaluacion` en `backend/app/models/`
- **Migración nueva**: tabla `evaluacion`, `reserva_evaluacion`, `resultado_evaluacion`
- **API nueva**: `/api/coloquios/*` con endpoints CRUD de convocatorias, importación, reservas, resultados y métricas
- **Permisos nuevos**: `coloquios:gestionar`, `coloquios:reservar`, `coloquios:ver` — agregar a seed de roles
- **Dependencia**: C-07 (usuarios) — necesario para relación con `Usuario` como alumno
