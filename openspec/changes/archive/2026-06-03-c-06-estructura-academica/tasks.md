## 1. Migración y Modelos

- [x] 1.1 Crear migración Alembic 007 para agregar tablas de `carreras`, `materias` y `cohortes` (con constraint unique compuesto)
- [x] 1.2 Implementar modelo SQLAlchemy `Carrera` con `tenant_id`, `codigo`, `nombre`, `estado` y constraints
- [x] 1.3 Implementar modelo SQLAlchemy `Materia` con `tenant_id`, `codigo`, `nombre`, `estado` y constraints
- [x] 1.4 Implementar modelo SQLAlchemy `Cohorte` con `tenant_id`, `carrera_id`, `nombre`, `anio`, `vig_desde`, `vig_hasta`, `estado` y constraints
- [x] 1.5 Escribir tests unitarios para creación y constraint unicidad para los 3 modelos (aislamiento tenant)

## 2. Repositories y Schemas

- [x] 2.1 Definir esquemas Pydantic para `Carrera` (Create, Update, Response) con `extra='forbid'`
- [x] 2.2 Definir esquemas Pydantic para `Materia` (Create, Update, Response) con `extra='forbid'`
- [x] 2.3 Definir esquemas Pydantic para `Cohorte` (Create, Update, Response) con `extra='forbid'`
- [x] 2.4 Implementar repositorios `CarreraRepository`, `MateriaRepository` y `CohorteRepository` extendiendo `BaseRepository`
- [x] 2.5 Escribir tests de integración para Repositories para asegurar filtrado automático por `tenant_id`

## 3. Services (Lógica de Negocio)

- [x] 3.1 Implementar `CarreraService` con validaciones de alta/edición
- [x] 3.2 Implementar `MateriaService` con validaciones de alta/edición
- [x] 3.3 Implementar `CohorteService` con validación: "carrera inactiva no admite cohortes abiertas"
- [x] 3.4 Escribir tests integración comprobando que `CohorteService` rechace creación si `Carrera` está inactiva

## 4. Routers y Endpoints

- [x] 4.1 Implementar router `/api/admin/carreras` y conectarlo a app principal
- [x] 4.2 Proteger router `/api/admin/carreras` con `require_permission("estructura:gestionar")`
- [x] 4.3 Implementar router `/api/admin/materias` y conectarlo a app principal
- [x] 4.4 Proteger router `/api/admin/materias` con `require_permission("estructura:gestionar")`
- [x] 4.5 Implementar router `/api/admin/cohortes` y conectarlo a app principal
- [x] 4.6 Proteger router `/api/admin/cohortes` con `require_permission("estructura:gestionar")`
- [x] 4.7 Escribir tests E2E de API validando status 201, status 400/409 (por validación/unicidad) y status 403 (RBAC)
