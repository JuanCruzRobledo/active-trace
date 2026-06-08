# Design: c-24-frontend-finanzas-y-admin

## Arquitectura

### Patrón General

Cada feature sigue el mismo patrón establecido en C-22/C-23:

```
features/{nombre}/
├── components/     ← Componentes de presentación (opcional)
├── hooks/          ← TanStack Query hooks (useQuery / useMutation)
├── services/       ← Llamadas HTTP via el api client (Axios)
├── types/          ← Schemas Zod + tipos inferidos
└── pages/          ← Páginas container que arman la vista
```

Shared components reutilizables YA existen en `frontend/src/shared/components/`:
`FilterableTable`, `ContextoAcademicoSelector`, `ConfirmDialog`, `FormField`, `Input`, `Button`, `ErrorMessage`, `LoadingSpinner`. Este change los **reutiliza** — no crea nuevos shared salvo necesidad puntual.

### Componentes Principales

| Módulo | Componentes Clave | Descripción |
|--------|-------------------|-------------|
| **liquidaciones** | `LiquidacionPeriodoPage`, `SegmentoLiquidacionTable`, `LiquidacionKpiHeader`, `DetalleDocenteDialog`, `HistorialLiquidacionesPage`, `GrillaSalarialPage`, `FacturasPage` | Vista segmentada, cierre, historial, grilla salarial, facturas |
| **estructura-academica** | `CarrerasPage`, `CohortesPage`, `MateriasPage` (ABM cada una) | ABM de estructura académica |
| **usuarios-tenant** | `UsuariosListPage`, `UsuarioFormPage` | ABM de usuarios del tenant |
| **auditoria** | `AuditoriaPanelPage`, `AccionesPorDiaChart`, `ComunicacionesPorDocentePanel`, `InteraccionesPanel`, `LogAuditoriaPage` | Panel de métricas + log completo |

### Navegación

Se actualiza `AppLayout` para incluir, según permisos del usuario:

```
Finanzas            (rol FINANZAS / ADMIN)
├── Liquidaciones del Período   (liquidaciones:ver)
├── Historial                   (liquidaciones:ver)
├── Grilla Salarial             (liquidaciones:configurar-salarios)
└── Facturas                    (liquidaciones:ver)
Administración      (rol ADMIN)
├── Carreras                    (estructura:gestionar)
├── Cohortes                    (estructura:gestionar)
├── Materias                    (estructura:gestionar)
├── Usuarios                    (usuarios:gestionar)
└── Auditoría                   (auditoria:ver)
```

### Flujo de Datos

1. Cada página carga datos mediante hooks TanStack Query → `services/{modulo}.ts` → api client → backend
2. Las mutaciones (POST/PATCH/DELETE) usan `useMutation` con invalidación de queries relacionadas
3. Los formularios usan React Hook Form + Zod (schemas con `.strict()` — regla dura del proyecto)
4. Las tablas filtrables usan el `FilterableTable` compartido

### APIs Consumidas (ya existentes en backend — paths verificados)

> Los prefijos reales de los routers son `/api/...` (NO `/api/v1/...`). Verificado en `backend/app/api/v1/routers/`.

#### Liquidaciones — `liquidaciones.py` (prefix `/api/liquidaciones`)

| Acción | Endpoint |
|--------|----------|
| Calcular liquidación del período | `POST /api/liquidaciones/calcular` |
| Listar liquidaciones | `GET /api/liquidaciones` |
| Detalle de una liquidación | `GET /api/liquidaciones/{liquidacion_id}` |
| Cerrar liquidación | `POST /api/liquidaciones/{liquidacion_id}/cerrar` |
| Salarios base (listar / crear) | `GET` / `POST /api/liquidaciones/grilla/salarios-base` |
| Salarios plus (listar / crear) | `GET` / `POST /api/liquidaciones/grilla/salarios-plus` |
| Claves plus (listar / crear) | `GET` / `POST /api/liquidaciones/grilla/claves-plus` |
| Clave plus (detalle / actualizar) | `GET` / `PATCH /api/liquidaciones/grilla/claves-plus/{clave_id}` |
| Facturas (listar / crear) | `GET` / `POST /api/liquidaciones/facturas` |
| Marcar factura abonada | `POST /api/liquidaciones/facturas/{factura_id}/abonar` |

#### Estructura académica + Usuarios — `admin_estructura.py` y `usuarios.py` (prefix `/api/admin`)

| Acción | Endpoint |
|--------|----------|
| Carreras (crear/listar/detalle/editar) | `POST` `GET /api/admin/carreras`, `GET` `PATCH /api/admin/carreras/{id}` |
| Materias (crear/listar/detalle/editar) | `POST` `GET /api/admin/materias`, `GET` `PATCH /api/admin/materias/{id}` |
| Cohortes (crear/listar/detalle/editar) | `POST` `GET /api/admin/cohortes`, `GET` `PATCH /api/admin/cohortes/{id}` |
| Usuarios (crear/listar/detalle/editar/baja) | `POST` `GET /api/admin/usuarios`, `GET` `PATCH` `DELETE /api/admin/usuarios/{id}` |

#### Auditoría — `auditoria.py` (prefix `/api/auditoria`)

| Acción | Endpoint |
|--------|----------|
| Acciones por día | `GET /api/auditoria/acciones-por-dia` |
| Comunicaciones por docente | `GET /api/auditoria/comunicaciones-por-docente` |
| Interacciones por docente×materia | `GET /api/auditoria/interacciones-por-docente-materia` |
| Últimas acciones | `GET /api/auditoria/ultimas-acciones` |
| Log completo | `GET /api/auditoria/log` |

### Permisos (RBAC)

Cada ruta se protege con `<RequirePermission>` usando los permisos del backend:

| Ruta | Permiso |
|------|---------|
| `/finanzas/liquidaciones` | `liquidaciones:ver` |
| `/finanzas/historial` | `liquidaciones:ver` |
| `/finanzas/liquidaciones/{id}/cerrar` (acción) | `liquidaciones:cerrar` |
| `/finanzas/grilla-salarial` | `liquidaciones:configurar-salarios` |
| `/finanzas/facturas` | `liquidaciones:ver` |
| `/admin/carreras`, `/admin/cohortes`, `/admin/materias` | `estructura:gestionar` |
| `/admin/usuarios` | `usuarios:gestionar` |
| `/admin/auditoria` | `auditoria:ver` |

## Views / UI Patterns

### Vista de Liquidación Segmentada (F10.6)

La página `LiquidacionPeriodoPage` muestra:

- **Cabecera de KPIs** (`LiquidacionKpiHeader`): "Total sin factura" y "Total con factura"
- **Filtros**: cohorte, mes, docente específico (opcional)
- **Tres segmentos** renderizados como tablas independientes (`SegmentoLiquidacionTable`):
  1. **Detalle general**: PROFESOR, TUTOR, COORDINADOR que no facturan
  2. **NEXO**: calculado por separado, sumado al total general
  3. **Docentes que facturan**: informativo, excluido del total (su pago va por Facturas)
- **Acciones**: vista previa de detalle individual (`DetalleDocenteDialog`), cerrar liquidación (con `ConfirmDialog`), ir al historial, ir a grilla salarial

### Cierre de Liquidación (F10.2)

Acción irreversible → siempre detrás de `ConfirmDialog`. Tras el cierre exitoso, la liquidación queda marcada como inmutable (badge "Cerrada") y las acciones de modificación se deshabilitan. Se invalida la query del período.

### ABM Grilla Salarial (F10.4)

`GrillaSalarialPage` con dos secciones tabulares con vigencia temporal:
- **Salarios base**: importe por rol (PROFESOR/TUTOR/NEXO/COORDINADOR) con vigencia desde/hasta
- **Plus**: identificados por clave, rol y descripción, también con vigencia

Cada sección usa `FilterableTable` + formulario de alta (RHF + Zod).

### Gestión de Facturas (F10.5)

`FacturasPage` con `FilterableTable`: filtros por docente, estado (pendiente/abonada), rango de fechas y búsqueda libre. Acción principal: marcar como abonada (`POST .../abonar`) detrás de confirmación.

### Panel de Auditoría (F9.1 / FL-11)

`AuditoriaPanelPage` con filtros compartidos (rango de fechas, materia, usuario, estado de actividad) que alimentan cuatro sub-vistas vía hooks independientes: gráfico de acciones por día, comunicaciones por docente, interacciones por docente×materia, y registro de últimas acciones. El `LogAuditoriaPage` muestra el log completo con todos los campos (fecha/hora, usuario, materia, acción, registros afectados, IP, user agent).

## Consideraciones

- **Governance BAJO**: el backend de finanzas (dominio CRÍTICO) ya está implementado, probado y archivado. Este change solo añade UI que lo consume.
- **Inmutabilidad en UI**: el frontend debe reflejar el estado "cerrada" de una liquidación deshabilitando acciones de modificación; la garantía real de inmutabilidad la impone el backend (RN-22).
- **Separación contable**: los docentes que facturan NO entran en el total de la liquidación general (RN-35). La UI los muestra de forma informativa pero claramente segregada.
- **Trade-off**: ABM de carreras/cohortes/materias podrían unirse en una sola página con tabs; se mantienen separados por claridad de navegación y consistencia con la estructura del backend.
- **Dependencia de schemas**: aunque los routers existen, los DTOs de respuesta deben validarse contra los schemas Pydantic reales durante apply.
- **Prefijos de API**: usar `/api/...` (no `/api/v1/...`) — verificado en los routers. Esto corrige la convención documentada en el design de C-23.
