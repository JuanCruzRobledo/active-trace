## Context

El frontend actual (C-21) tiene el shell completo: layout autenticado (AppLayout), sistema de rutas protegidas (ProtectedRoute, RequirePermission), cliente HTTP centralizado con refresh transparente (api.ts), hook de auth (useAuth), y página de Dashboard. Todas las APIs de backend que consume C-22 ya existen (C-10 calificaciones/padrón, C-11 análisis/umbral/rankings/monitores, C-12 comunicaciones), incluyendo sus endpoints REST documentados y tests.

C-22 agrega las páginas y componentes que los usuarios PROFESOR, TUTOR y COORDINADOR necesitan para operar la plataforma: importar datos, analizar atrasados, comunicarse con alumnos.

## Goals / Non-Goals

**Goals:**
- Feature module `features/comision/` con 6 sub-secciones: importación, umbral, atrasados, rankings, reportes, comunicaciones
- Feature module `features/monitores/` con monitor de seguimiento tutor/profesor
- Consumir APIs existentes sin modificar backend
- Tests de componentes e integración con mocks de API
- Navegación integrada al menú lateral existente (AppLayout)
- Protección de rutas por permiso via RequirePermission

**Non-Goals:**
- No modificar el backend ni agregar endpoints nuevos
- No implementar la vista de coordinación (C-23) ni finanzas (C-24)
- No implementar mensajería interna (ya cubierta en C-20 frontend)
- No implementar el tablón de avisos (C-23)

## Decisions

### 1. Feature modules separados por dominio funcional
- `features/comision/` agrupa todo lo que un profesor ve de su comisión
- `features/monitores/` agrupa las vistas de seguimiento transversal
- Cada módulo contiene `{components,hooks,services,pages}` como dicta la convención del proyecto
- **Alternativa descartada**: un solo módulo gigante `features/docente/` — dificulta el mantenimiento y el paralelismo entre agentes

### 2. Cada página es un TanStack Query hook dedicado
- Cada página de lista/tabla tiene su propio hook `useXxx()` en `services/` que envuelve `api.get()` con `useQuery`
- Las mutaciones (importar, enviar) usan `useMutation` con invalidación de queries relacionadas
- **Alternativa descartada**: un service genérico — los hooks específicos son más testeables y predecibles

### 3. Preview de importación en 2 pasos (dry-run → confirmar)
- Paso 1: POST a `/api/v1/calificaciones/preview` → devuelve filas parseadas + detección de conflictos
- Paso 2: usuario revisa y confirma → POST a `/api/v1/calificaciones/importar`
- Consistente con el flujo de F1.1 (importar con preview antes de persistir)

### 4. Tracking de comunicaciones en tiempo real via polling
- El worker de comunicaciones (C-12) actualiza estados asincrónicamente
- La UI hace polling cada 5s del estado de la comunicación activa via `useQuery` con `refetchInterval: 5000`
- **Alternativa descartada**: WebSockets — infraestructura adicional sin beneficio claro para polling cada 5s

### 5. Estructura de routing
```
/                        → Dashboard (existente)
/comision                → Página principal de comisión (selector de materia)
/comision/:materiaId/importar  → Importación de calificaciones
/comision/:materiaId/umbral    → Configurar umbral de aprobación
/comision/:materiaId/atrasados → Vista de alumnos atrasados
/comision/:materiaId/rankings  → Ranking y notas finales
/comision/:materiaId/reportes  → Reportes rápidos + export
/comision/:materiaId/comunicaciones → Comunicación a atrasados
/monitores               → Monitor de seguimiento (tutor/profesor)
```

## Risks / Trade-offs

- **[Riesgo] Polling cada 5s en comunicaciones activas**: si muchos usuarios abren la misma comunicación simultáneamente, puede generar carga. → Mitigación: el polling solo ocurre mientras la comunicación tiene estado `Pendiente` o `En envío`. Al llegar a `Enviado`/`Fallido`/`Cancelado`, el polling se detiene.
- **[Riesgo] Importación dry-run con archivos grandes**: archivos con muchas filas pueden demorar. → Mitigación: mostrar indicador de carga (LoadingSpinner) y límite sugerido de 2000 filas por importación.
- **[Trade-off] Sin debounce en filtros de monitores**: las queries se ejecutan al cambiar cada filtro. Aceptable porque son queries indexadas por tenant + materia.
