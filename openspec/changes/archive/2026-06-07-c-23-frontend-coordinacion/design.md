# Design: c-23-frontend-coordinacion

## Arquitectura

### Patrón General

Cada feature sigue el mismo patrón establecido en C-22:

```
features/{nombre}/
├── components/     ← Componentes puramente de presentación (opcional)
├── hooks/          ← TanStack Query hooks (useQuery / useMutation)
├── services/       ← Llamadas HTTP via Axios (api client)
├── types/          ← Schemas Zod + tipos inferidos
└── pages/          ← Páginas que arman la vista (container components)
```

Shared components reutilizables viven en `frontend/src/shared/components/`.

### Componentes Principales

| Módulo | Componentes Clave | Descripción |
|--------|-------------------|-------------|
| **equipos-docentes** | `MisEquiposPage`, `AsignacionesPage`, `AsignacionMasivaPage`, `ClonarEquipoPage`, `VigenciaEquipoPage`, `ExportarEquipoPage` | Gestión completa de equipos docentes (vista propia + admin) |
| **avisos** | `AvisosListPage`, `AvisoFormPage`, `AvisoDetailPage`, `AckTrackingPanel` | ABM de avisos con timeline, acknowledgment tracking |
| **tareas** | `MisTareasPage`, `AsignarTareaPage`, `TareasAdminPage`, `TareaDetailPanel` | Workflow de tareas internas |
| **encuentros-admin** | `EncuentrosAdminPage` | Vista transversal de encuentros |
| **coloquios** | `ColoquiosPanelPage`, `ConvocatoriaFormPage`, `ConvocatoriaListPage`, `ColoquiosAdminPage` | Gestión de coloquios y convocatorias |
| **guardias** | `GuardiasPage` | Registro y consulta de guardias |
| **programas** | `ProgramasPage` | Subir y gestionar programas |
| **fechas-academicas** | `FechasAcademicasPage` | Gestión de fechas de evaluaciones |
| **setup-cuatrimestre** | `SetupCuatrimestreWizard` | Flujo multi-paso FL-03 |

### Navegación

Se actualiza `AppLayout` para incluir un menú con las siguientes secciones para COORDINADOR/ADMIN:

```
Dashboard
Comisiones (existente)
Monitores (existente + mejorado)
├── Monitor General (F2.7)
├── Monitor Seguimiento (F2.9)
Coordinación
├── Equipos Docentes
│   ├── Mis Equipos
│   ├── Asignaciones
│   ├── Asignación Masiva
│   ├── Clonar Equipo
│   └── Exportar
├── Avisos
├── Tareas
├── Encuentros
├── Coloquios
├── Guardias
├── Programas
├── Fechas Académicas
└── Setup de Cuatrimestre
```

### Flujo de Datos

1. Cada página carga datos mediante hooks TanStack Query → `services/{modulo}.ts` → Axios → API backend
2. Las mutaciones (POST/PUT/PATCH/DELETE) usan `useMutation` con invalidación de queries relacionadas
3. Los formularios usan React Hook Form + Zod para validación tipada client-side
4. Los componentes de tabla filtrable (patrón común) se abstraen en shared components

### APIs Consumidas (ya existentes en backend)

Basado en los routers existentes en `backend/app/api/v1/routers/`:

| Módulo | Endpoints Clave |
|--------|----------------|
| **equipos** | `GET /api/v1/equipos/mis-equipos`, `GET /api/v1/equipos/asignaciones`, `POST /api/v1/equipos/asignaciones/masiva`, `POST /api/v1/equipos/clonar`, `PATCH /api/v1/equipos/{id}/vigencia`, `GET /api/v1/equipos/exportar` |
| **avisos** | `GET /api/v1/avisos`, `POST /api/v1/avisos`, `PUT /api/v1/avisos/{id}`, `DELETE /api/v1/avisos/{id}`, `GET /api/v1/avisos/timeline`, `POST /api/v1/avisos/{id}/acknowledge`, `GET /api/v1/avisos/{id}/tracking` |
| **tareas** | `GET /api/v1/tareas/mias`, `GET /api/v1/tareas`, `POST /api/v1/tareas`, `GET /api/v1/tareas/{id}`, `PATCH /api/v1/tareas/{id}/estado`, `POST /api/v1/tareas/{id}/comentarios` |
| **encuentros** | `GET /api/v1/encuentros` (admin — todos los encuentros del tenant) |
| **coloquios** | `GET /api/v1/coloquios/metricas`, `GET /api/v1/coloquios/convocatorias`, `POST /api/v1/coloquios/convocatorias`, `POST /api/v1/coloquios/alumnos`, `GET /api/v1/coloquios/admin` |
| **guardias** | `GET /api/v1/guardias`, `POST /api/v1/guardias`, `PATCH /api/v1/guardias/{id}`, `GET /api/v1/guardias/exportar` |
| **programas** | `GET /api/v1/programas`, `POST /api/v1/programas`, `GET /api/v1/programas/{id}`, `DELETE /api/v1/programas/{id}` |
| **fechas-academicas** | `GET /api/v1/fechas-academicas`, `POST /api/v1/fechas-academicas`, `PATCH /api/v1/fechas-academicas/{id}`, `DELETE /api/v1/fechas-academicas/{id}`, `GET /api/v1/fechas-academicas/lms-export` |
| **monitores** | `GET /api/v1/monitores/general`, `GET /api/v1/monitores/seguimiento` (ya consumido en feature existente) |

### Permisos (RBAC)

Cada ruta en el frontend se protege con `<RequirePermission>` usando los mismos permisos que el backend:

| Ruta | Permiso |
|------|---------|
| `/equipos/*` | `equipos:ver` / `equipos:asignar` |
| `/avisos/*` | `avisos:publicar` / `avisos:gestionar` |
| `/tareas/*` | `tareas:ver` / `tareas:asignar` |
| `/encuentros/*` | `encuentros:ver` |
| `/coloquios/*` | `coloquios:gestionar` |
| `/guardias/*` | `guardias:ver` |
| `/programas/*` | `estructura:gestionar` |
| `/fechas-academicas/*` | `estructura:gestionar` |
| `/setup-cuatrimestre/*` | `equipos:asignar` + `estructura:gestionar` |

## Views / UI Patterns

### Tabla Filtrable (Shared Component)

Se crea un componente `FilterableTable` en shared que encapsula:
- Búsqueda por texto libre
- Filtros por select/dropdown (materia, cohorte, estado, rol, etc.)
- Paginación
- Ordenamiento por columna
- Exportación a CSV
- Estado vacío y estados de carga/error

### Formulario con Selectores de Contexto

Para features que requieren seleccionar materia × carrera × cohorte (asignaciones, programas, fechas), se crea un `ContextoAcademicoSelector` compartido que carga las opciones vía TanStack Query y maneja dependencias en cascada.

### Timeline de Avisos

El aviso timeline usa un layout vertical con tarjetas expandibles que muestran:
- Título, severidad (con color), fechas de vigencia
- Roles destino y alcance
- Estado de acknowledgment (checklist de quién confirmó y quién no)

## Consideraciones

- **Trade-off**: Algunos módulos son muy pequeños (guardias, programas) y podrían agruparse en una sola página. Se mantienen separados para consistencia con la estructura del backend y para facilitar la navegación.
- **Alternativa considerada**: Hacer una SPA monolítica de coordinación (descartada porque los módulos tienen ciclos de vida independientes y diferentes conjuntos de permisos).
- **Reutilización**: El `FilterableTable` compartido evita duplicar lógica de tabla filtrable en cada módulo.
- **Dependencia de backend endpoints**: Aunque los routers existen, los schemas de respuesta deben validarse contra lo que realmente devuelve cada endpoint. Cualquier discrepancia se resolverá en apply.
