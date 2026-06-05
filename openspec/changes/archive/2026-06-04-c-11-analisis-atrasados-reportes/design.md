## Context

C-11 es el primer change puramente analítico del flujo central. No crea nuevas entidades ni tablas — toda la lógica opera sobre los modelos existentes de C-10 (`Calificacion`, `UmbralMateria`) y cambios anteriores (`Asignacion`, `EntradaPadron`, `Materia`). Los cómputos (atrasados, ranking, notas finales) son consultas de agregación con filtros por tenant, materia, cohorte y rol.

El sistema actual corre sobre FastAPI + SQLAlchemy 2.0 async con PostgreSQL. Cada cambio anterior agregó routers en `backend/app/api/v1/routers/`, services en `backend/app/services/`, repositories en `backend/app/repositories/`, schemas en `backend/app/schemas/` y tests en `backend/tests/`.

## Goals / Non-Goals

**Goals:**
- Proveer endpoints REST para cómputo de alumnos atrasados (RN-06) con scope por materia y rol
- Ranking de actividades aprobadas (RN-09) excluyendo alumnos sin ninguna aprobada
- Reportes rápidos por materia con métricas clave (total alumnos, aprobados, atrasados, %)
- Notas finales agrupadas por alumno a partir de actividades seleccionadas
- Exportación de TPs sin corregir (RN-07, RN-08) — solo actividades textuales
- Monitor general (F2.7) con filtros materia/regional/comisión/estado
- Monitor de seguimiento (F2.8) con filtros por alumno/correo/comisión/regional/actividad/mínimo
- Monitor extendido (F2.9) con rango de fechas adicional
- Scope multi-tenant: cada query filtra por tenant_id del usuario autenticado
- Guard `atrasados:ver` en todos los endpoints

**Non-Goals:**
- No se crean nuevos modelos de datos ni migraciones
- No se modifica el modelo `Calificacion` ni `UmbralMateria`
- No se implementa comunicación con alumnos (es C-12)
- No se implementan dashboards UI (es frontend, Fase 5)
- No se implementa caché de cómputos (los cálculos son sobre datos actuales)
- No se implementa paginación en monitores (el alcance natural es una comisión ~30-50 alumnos)

## Decisions

### D1: Service único de análisis vs múltiples
**Decisión**: Un solo `AnalisisService` con métodos separados por funcionalidad.
**Rationale**: Todos los cómputos comparten las mismas dependencias (session, tenant_id, repositorio de análisis). Un service único evita duplicación de inyección y factories. Los métodos son suficientemente cohesivos (todos son consultas de agregación sobre el mismo modelo de datos).
**Alternativa descartada**: Services separados por feature — introduce sobre-ingeniería para la cohesión actual.

### D2: Repository con queries de agregación vs raw SQL
**Decisión**: Un `AnalisisRepository` con consultas SQLAlchemy 2.0 (select + func + group_by) para cada cómputo.
**Rationale**: Las agregaciones (COUNT, AVG, filtros condicionales) se expresan naturalmente en SQLAlchemy ORM. Mantiene la capa de abstracción Repository y permite testear las queries unitariamente.
**Alternativa descartada**: SQL raw — rompe la abstracción y dificulta el testeo con base real.

### D3: Cómputo en memoria vs base de datos
**Decisión**: El cómputo de atrasados se hace en dos pasos: (1) repository obtiene todas las calificaciones + umbral de la materia en una query, (2) service clasifica cada alumno como atrasado/no-atrasado en Python.
**Rationale**: El volumen de datos por materia/comisión es pequeño (decenas de alumnos, ~5-15 actividades). La lógica de clasificación (RN-06: faltante OR nota < umbral) es más fácil de testear y mantener en Python que en SQL.
**Alternativa descartada**: Clasificación vía SQL con CASE — frágil y difícil de mantener.

### D4: Export como endpoint JSON vs generación de archivo
**Decisión**: El export de TPs sin corregir devuelve JSON estructurado. La generación de archivo descargable (CSV/XLSX) se delega al frontend.
**Rationale**: Consistencia con el resto de la API. Si se necesita descarga nativa, se agrega un formato parameter posteriormente.

## API Design

```
GET  /api/analisis/atrasados?materia_id=&cohorte_id=&comision=
     → {alumnos_atrasados: [...], total_alumnos: N, porcentaje: N}
     Guard: atrasados:ver

GET  /api/analisis/ranking?materia_id=&cohorte_id=&comision=
     → {ranking: [{alumno_id, nombre, apellidos, cantidad_aprobadas, total_actividades}], ...}
     Filtro: solo alumnos con >= 1 aprobada (RN-09)
     Guard: atrasados:ver

GET  /api/analisis/reporte-rapido?materia_id=&cohorte_id=
     → {total_alumnos, aprobados, atrasados, porcentaje_aprobacion, cantidad_actividades}
     Guard: atrasados:ver

GET  /api/analisis/notas-finales?materia_id=&cohorte_id=&comision=&actividades[]=
     → {notas: [{alumno_id, nombre, apellidos, promedio, aprobado}], ...}
     Guard: atrasados:ver

GET  /api/analisis/tps-sin-corregir?materia_id=&cohorte_id=&comision=
     → {pendientes: [{alumno_id, nombre, actividad, entregado_at}], ...}
     Solo actividades textuales (RN-08)
     Guard: atrasados:ver

GET  /api/analisis/monitor-general?materia_id=&regional=&comision=&estado=&q=
     → {alumnos: [{id, nombre, ...}], total, filtros_aplicados}
     Guard: atrasados:ver (COORDINADOR, ADMIN)

GET  /api/analisis/monitor-seguimiento?alumno_id=&email=&comision=&regional=&actividad=&min_aprobadas=
     → {alumnos: [{id, nombre, actividades: [...]}], ...}
     Guard: atrasados:ver (TUTOR, PROFESOR)

GET  /api/analisis/monitor-seguimiento?fecha_desde=&fecha_hasta=&...  (mismos filtros que F2.8)
     → {alumnos: [...], ...}
     Guard: atrasados:ver (COORDINADOR, ADMIN) — extensión con rango de fechas
```

## Risks / Trade-offs

- **[Rendimiento]**: Las queries de agregación sobre `Calificacion` sin índices compuestos pueden ser lentas en materias con muchos alumnos (>200). **Mitigación**: agregar índice compuesto `(tenant_id, materia_id, actividad)` si las pruebas de carga lo justifican.
- **[Scope de datos]**: El monitor general (F2.7) puede devolver muchos registros. **Mitigación**: el alcance natural está acotado por materia + cohorte, no es una query global sin filtros.
- **[Precisión de atrasados]**: La clasificación de atrasados depende de que el umbral esté configurado. **Mitigación**: si no existe `UmbralMateria` para la asignación, se usa el default 60%.

## Open Questions

- ¿El monitor general (F2.7) debe permitir filtro *sin* materia? (alcance global del tenant). Por ahora se requiere materia_id como obligatorio.
- Formato de export: JSON inicialmente. ¿Se requiere CSV descargable desde el backend más adelante?
