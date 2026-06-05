## Context

C-13 implementa los módulos de Encuentros y Guardias del sistema. Con C-08 (equipos docentes) y C-07 (usuarios y asignaciones) ya completados, el sistema tiene la capacidad de identificar qué PROFESOR está asignado a qué materia/cohorte. Este change agrega la capa de planificación y registro de actividades sincrónicas.

El modelo de datos ya está definido en la KB:
- **SlotEncuentro (E9)**: plantilla de recurrencia con día_semana, hora, fecha_inicio, cant_semanas o fecha_unica
- **InstanciaEncuentro (E10)**: encuentro concreto con estado propio, meet_url, video_url, comentario
- **Guardia (E11)**: registro de atención con día, horario, estado, comentarios

La arquitectura actual sigue Clean Architecture con FastAPI async, SQLAlchemy 2.0, multi-tenancy row-level por tenant_id, y repositorios genéricos con scope de tenant forzado.

## Goals / Non-Goals

**Goals:**
- Modelos SQLAlchemy para SlotEncuentro, InstanciaEncuentro, Guardia con tenant isolation
- Migración Alembic para las 3 tablas
- Endpoint `POST /api/encuentros/slots` — crear slot recurrente o único con generación automática de instancias (RN-13)
- Endpoint `POST /api/encuentros/instancias` — crear instancia independiente (sin slot)
- Endpoint `PATCH /api/encuentros/instancias/{id}` — editar estado, meet_url, video_url, comentario (RN-14)
- Endpoint `GET /api/encuentros/instancias` — listar instancias con filtros (materia, fechas, estado, slot_id)
- Endpoint `GET /api/encuentros/slots` — listar slots del usuario/tenant
- Endpoint `GET /api/encuentros/{materia_id}/exportar-aula` — bloque HTML embebible
- Endpoint `POST /api/guardias` — registrar guardia
- Endpoint `GET /api/guardias` — listar guardias con filtros (docente, materia, fechas, estado)
- Endpoint `PATCH /api/guardias/{id}` — editar estado/comentarios
- Endpoint `GET /api/guardias/exportar` — exportar guardias a archivo
- Permisos seed en matriz RBAC para los 4 nuevos permisos
- Audit log para creación/modificación de encuentros y guardias
- Scope multi-tenant en todas las queries

**Non-Goals:**
- No se implementa frontend de encuentros/guardias (es Fase 5, C-23)
- No se implementa integración real con videoconferencia (Zoom/Meet) — meet_url es texto libre
- No se implementa notificación automática a alumnos al crear encuentros
- No se implementa recurrencia con excepciones (ej: "saltar feriado") — las instancias se generan secuencialmente
- No se implementa aprobación de guardias por coordinación — el registro es directo
- No se implementa vinculación con coloquios (C-14) ni con fechas académicas (C-17)

## Decisions

### D1: Generación de instancias en el service, no en la DB
**Decisión**: La lógica de generación de N instancias a partir de un slot recurrente se implementa en `encuentro_service.py` usando Python datetime, no como función de base de datos (trigger, procedure).
**Rationale**: La generación semanal es un bucle simple: para i in range(cant_semanas), sumar i*7 días a fecha_inicio. Hacerlo en Python mantiene la lógica testeable y evita migrar lógica de negocio a la DB. La generación ocurre en una sola transacción (repository inserta todas las instancias).
**Alternativa descartada**: Generar con `generate_series` de PostgreSQL — ata la lógica a PostgreSQL, difícil de testear unitariamente.

### D2: Slot vs Instancia — dos modelos separados, no uno solo
**Decisión**: SlotEncuentro e InstanciaEncuentro son modelos separados con FK slot_id → InstanciaEncuentro (nullable). No se usa un único modelo con un flag "es_recurrente".
**Rationale**: Refleja el modelo conceptual de la KB (E9, E10). Permite que cada instancia tenga su propio estado independiente (RN-14). El slot es la "plantilla" y la instancia es el "evento real". Si se usara un solo modelo, la lógica de recurrencia contaminaría cada registro.
**Alternativa descartada**: Modelo único con slot_id nullable que se referencia a sí mismo — complejidad innecesaria, viola separación de conceptos.

### D3: Exportación de aula como generación de HTML server-side
**Decisión**: El endpoint `GET /encuentros/{materia_id}/exportar-aula` genera HTML server-side combinando los encuentros programados con las grabaciones disponibles en una tabla/cards formateadas.
**Rationale**: F6.4 requiere un fragmento listo para copiar y pegar en el LMS. Generar HTML server-side es simple, no requiere librerías adicionales y produce un string que el frontend muestra al usuario para copiar.
**Alternativa descartada**: Generar en frontend — el contenido debe ser portable y autónomo (HTML plano), no depende de JavaScript.

### D4: Guardias como entidad independiente, no submodelo de encuentros
**Decisión**: Guardia es un modelo separado con sus propios endpoints, no un tipo de InstanciaEncuentro.
**Rationale**: La guardia tiene semántica diferente (atención a alumnos, no clase sincrónica), actores diferentes (TUTOR principalmente vs PROFESOR), y campos distintos (día + horario como rango, no fecha+ hora fija). Compartir modelo forzaría columnas nulas y lógica condicional.
**Alternativa descartada**: Guardia como subtipo de encuentro — falsa generalización, complica queries y validaciones.

### D5: Permisos con scope (propio) para PROFESOR/TUTOR
**Decisión**: `encuentros:gestionar` y `guardias:registrar` verifican que el usuario tiene asignación activa en la materia (scope propio). COORDINADOR y ADMIN ven todo el tenant.
**Rationale**: Sigue el patrón de `equipos:asignar` y `calificaciones:importar` de C-08 y C-10. Un PROFESOR solo gestiona encuentros de sus materias; un COORDINADOR supervisa todo.
**Implementación**: El guard recibe `materia_id` (opcional). Si el usuario es COORDINADOR/ADMIN → pasa. Si es PROFESOR → verifica asignación activa en la materia.

## API Design

```
# Encuentros - Slots
POST /api/encuentros/slots
  Request: {materia_id, titulo, hora, dia_semana, fecha_inicio, cant_semanas, meet_url}
    o: {materia_id, titulo, hora, fecha_unica, meet_url}  # modo único
  Response: {slot: SlotResponse, instancias: [InstanciaResponse]}
  Guard: encuentros:gestionar

GET /api/encuentros/slots
  Query: materia_id? estado?
  Response: {items: [SlotResponse], total}
  Guard: encuentros:gestionar (propio) | encuentros:ver-admin

PATCH /api/encuentros/slots/{id}
  Request: {titulo?, hora?, meet_url?}
  Response: SlotResponse
  Guard: encuentros:gestionar

DELETE /api/encuentros/slots/{id}
  → Soft-delete del slot + todas sus instancias
  Guard: encuentros:gestionar

# Encuentros - Instancias
POST /api/encuentros/instancias
  Request: {materia_id, titulo, fecha, hora, meet_url}
  Response: InstanciaResponse (201)
  Guard: encuentros:gestionar

GET /api/encuentros/instancias
  Query: materia_id? slot_id? desde? hasta? estado?
  Response: {items: [InstanciaResponse], total}
  Guard: encuentros:gestionar (propio) | encuentros:ver-admin

PATCH /api/encuentros/instancias/{id}
  Request: {estado?, meet_url?, video_url?, comentario?}
  Response: InstanciaResponse
  Guard: encuentros:gestionar

# Exportación LMS
GET /api/encuentros/{materia_id}/exportar-aula
  Response: {html: "<bloque HTML>"}
  Guard: encuentros:gestionar

# Guardias
POST /api/guardias
  Request: {materia_id, carrera_id, cohorte_id, dia, horario, comentarios?}
  Response: GuardiaResponse (201)
  Guard: guardias:registrar

GET /api/guardias
  Query: materia_id? usuario_id? desde? hasta? estado?
  Response: {items: [GuardiaResponse], total}
  Guard: guardias:registrar (propio) | guardias:ver-admin

PATCH /api/guardias/{id}
  Request: {estado?, comentarios?}
  Response: GuardiaResponse
  Guard: guardias:registrar (propio si es TUTOR) | guardias:ver-admin

GET /api/guardias/exportar
  Query: mismos filtros que GET /guardias
  Response: archivo descargable (xlsx o csv)
  Guard: guardias:ver-admin
```

## Risks / Trade-offs

- **[Medio] Consistencia entre slot e instancias al modificar slot**: Si se modifica el slot (ej: hora), las instancias ya generadas NO se actualizan automáticamente. **Mitigación**: Es un trade-off intencional por RN-14 (cada instancia tiene estado independiente). El slot es la plantilla; las instancias futuras se crearían con los nuevos valores si se regenera el slot, pero las existentes mantienen sus datos. No hay actualización en cascada.
- **[Bajo] Generación de instancias en transacción grande**: Un slot con `cant_semanas=30` genera 30 instancias en una sola transacción. **Mitigación**: Es una operación administrativa (no concurrente, no frecuente). 30 inserciones en una transacción no representan problema de performance. Si en el futuro se necesitan 100+ semanas, se puede paginar la generación con un worker.
- **[Bajo] Exportación HTML sin estilos**: El HTML generado es plano (sin CSS externo) para ser portable. **Mitigación**: Se usan estilos inline básicos (tabla, borders, colores) para que se vea bien embebido en el LMS sin depender de estilos del sistema.
- **[Medio] PA-05 y PA-12 como preguntas abiertas**: El flujo de creación de guardias (PA-05) y el alcance de la vista admin de encuentros (PA-12) no están 100% cerrados. **Mitigación**: Se adoptan las decisiones más conservadoras y alineadas con el CHANGES.md: (a) guardias se crean desde el módulo dedicado, el TUTOR registra las propias y el COORDINADOR ve todas; (b) la vista admin de encuentros muestra todos los encuentros del tenant pero SOLO consulta, no permite editar en nombre de otro (editar requiere ser el creador o ADMIN).

## Migration Plan

1. Crear migración Alembic con las 3 tablas: `slot_encuentro`, `instancia_encuentro`, `guardia`, más enums `estado_encuentro`, `estado_guardia`, `dia_semana`
2. Aplicar migración en dev y verificar
3. Implementar modelos → schemas → repositorios → services → routers (en ese orden)
4. Seed de permisos en la tabla de catálogo (no hardcodeados, insert en `permisos` + `rol_permiso`)
5. Tests de integración por capa
6. Rollback: `alembic downgrade -1` revierte la migración sin perder datos de otros módulos