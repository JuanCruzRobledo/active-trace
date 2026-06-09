# Proposal: c-08-equipos-docentes

## Problema / Oportunidad

Actualmente existe el modelo `Asignacion` con CRUD básico (`C-07`), pero no hay operaciones de dominio específicas para gestionar **equipos docentes** como unidad: el coordinador no puede asignar múltiples docentes en bloque, clonar un equipo entre cuatrimestres, modificar la vigencia general ni exportar la composición del equipo. Cada operación requeriría múltiples llamadas al CRUD base, sin atomicidad ni auditoría específica.

## Solución Propuesta

Crear el módulo **equipos-docentes** como una capa de operaciones de dominio sobre `Asignacion`, exponiendo una API `/api/equipos/*` con estas capacidades:

1. **Mis equipos** (vista del docente): listar las asignaciones propias con su contexto académico.
2. **Asignación masiva**: asignar múltiples docentes × materia × carrera × cohorte × rol en una sola transacción, con autocompletado de usuarios (RN-30).
3. **Clonar equipo entre períodos**: duplicar asignaciones vigentes de un equipo origen a un destino, aplicando las fechas del nuevo período (RN-12).
4. **Modificar vigencia general**: actualizar `desde`/`hasta` de todas las asignaciones de un equipo en una operación.
5. **Exportar equipo**: generar archivo descargable con el detalle completo del equipo.

Todo esto requiere un nuevo permiso `equipos:ver` (para auto-consulta del docente), el uso del permiso existente `equipos:asignar` para operaciones de gestión, y registro de auditoría `ASIGNACION_MODIFICAR` en cada operación.

## Alcance

- [ ] Incluir:
  - Nuevo router `/api/equipos/*` con endpoints específicos
  - Nuevo permiso `equipos:ver` (seed en migración)
  - Nuevo service `EquipoService` con operaciones de dominio complejas
  - Listado de mis-equipos y gestión de asignaciones (F4.2, F4.3)
  - Asignación masiva con autocompletado (F4.4, RN-30)
  - Clonación de equipo entre períodos (F4.5, RN-12)
  - Modificación de vigencia general (F4.6)
  - Exportación de equipo a archivo (F4.7)
  - Nuevos schemas para cada operación
  - Audit logging en cada operación (`ASIGNACION_MODIFICAR`)
  - Tests completos: unitarios + integración

- [ ] Excluir:
  - Modificaciones al modelo `Asignacion` (no se necesita migración)
  - Administración de usuarios del equipo docente (F4.1 — ya cubierto por C-07)
  - Módulo de liquidaciones (C-18)
  - Frontend (será en C-23)

## Impacto

- **Backend**: Nuevo router, nuevo service, nuevos schemas, nueva migración de seed (permiso `equipos:ver`), audit logging
- **Frontend**: Ninguno (se implementa en C-23)
- **DB**: No requiere migración de schema — solo seed de permiso
- **Riesgos**:
  - Clonación masiva puede ser lenta si hay muchas asignaciones → mitigación: transacción única con logging
  - Asignación masiva sin transacción puede dejar estado inconsistente → mitigación: toda la operación dentro de una transacción
  - Governance ALTO → cualquier cambio requiere code review y tests antes de merge
