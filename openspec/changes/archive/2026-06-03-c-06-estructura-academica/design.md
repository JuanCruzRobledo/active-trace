## Context

El proyecto requiere estructurar el catálogo académico por cada tenant para dar soporte a alumnos, materias, cohortes y calificaciones. La arquitectura de Active Trace obliga a mantener el aislamiento estricto por `tenant_id` y a exponer los endpoints administrativos protegiéndolos mediante permisos precisos. Se definió según el ADR-006 que la Materia será un catálogo único a nivel de tenant y que las Carreras pueden contener Cohortes.

## Goals / Non-Goals

**Goals:**
- Implementar los modelos de base de datos para `Carrera`, `Cohorte` y `Materia` con soporte para multi-tenancy.
- Exponer tres routers con las rutas de CRUD (`/api/admin/carreras`, `/api/admin/cohortes`, `/api/admin/materias`).
- Asegurar los endpoints con `require_permission("estructura:gestionar")`.
- Validar las reglas de unicidad por tenant y coherencia de estado (una carrera inactiva no admite cohortes abiertas).

**Non-Goals:**
- Implementar las instancias de dictado (Dictado de materia en carrera/cohorte). Eso se hará en futuros changes (C-07+).
- Implementar la matriculación o carga de alumnos.
- Exponer endpoints públicos o para tutores en este change; todo es de uso exclusivo administrativo.

## Decisions

- **Unicidad compuesta en DB y aplicación:** Se implementarán constraints de base de datos (`UniqueConstraint`) y se manejará la excepción en los Repositories para convertirla en errores HTTP 400 amistosos. 
  - `Carrera`: `UniqueConstraint('tenant_id', 'codigo')`
  - `Materia`: `UniqueConstraint('tenant_id', 'codigo')`
  - `Cohorte`: `UniqueConstraint('tenant_id', 'carrera_id', 'nombre')`
- **Estados por Enum:** Se usarán enums simples de base de datos o tipos de SQLAlchemy para el estado (`Activa`, `Inactiva`) para simplificar el manejo de las transiciones lógicas.
- **Validación a nivel de Service:** La regla de negocio "carrera inactiva no admite cohortes abiertas" se verificará en el Service de `Cohorte` al momento de creación y edición, devolviendo error 400 si se incumple.
- **Uso de Repository Pattern Base:** Se extenderá de `BaseRepository[T]` para no duplicar código genérico de CRUD, inyectando el `tenant_id` en las operaciones.

## Risks / Trade-offs

- **[Risk] Complejidad en la unicidad:** Al tener eliminación lógica, los UNIQUE constraints pueden chocar con registros eliminados.
  - **Mitigation:** Las constraint de base de datos deben contemplar condiciones (Partial Indexes en PostgreSQL) o el campo `deleted_at`, por ejemplo: `UNIQUE(tenant_id, codigo) WHERE deleted_at IS NULL`. Si no es posible, se usará validación pura de aplicación en los Services.
- **[Risk] Cascada de eliminación o inactivación:** Inactivar una carrera podría dejar cohortes colgadas. 
  - **Mitigation:** Para C-06, como solo estamos creando catálogos, no implementaremos cascada automática. El usuario deberá gestionar el estado a mano o se levantará error si hay hijos activos (a definir si se rechaza, pero de entrada la regla habla sobre que no se puede abrir una cohorte en carrera inactiva).