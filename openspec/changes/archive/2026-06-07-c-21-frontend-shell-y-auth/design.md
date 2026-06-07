## Context

El backend de activia-trace expone APIs REST para auth (login, 2FA, recovery, refresh, logout, /me) y RBAC (permisos finos). No existe ningún frontend que las consuma. Se necesita construir una SPA desde cero con React 18 + TypeScript, usando Vite como bundler.

El frontend debe ser multi-tenant desde el día 0: el tenant se resuelve del JWT, no del frontend. El cliente HTTP centralizado maneja tokens de forma transparente.

## Goals / Non-Goals

**Goals:**
- Scaffolding completo del proyecto frontend con estructura feature-based
- Cliente HTTP Axios centralizado con interceptor de auth y refresh transparente
- Flujo completo de autenticación: login, 2FA (verificación y enrolamiento), recuperación de contraseña, logout
- Route guard que protege rutas según sesión activa y permisos RBAC
- Layout principal con sidebar/menú dinámico adaptado a los permisos del usuario
- Servicio Docker para frontend en docker-compose.yml

**Non-Goals:**
- Páginas de features de dominio (comisiones, alumnos, comunicaciones, etc.) — serán C-22, C-23, C-24
- Integración con Moodle SSO (ADR-001: será Fase 2)
- Pruebas E2E con Playwright (se agregan en C-22+ cuando haya páginas de dominio)
- SEO o renderizado server-side (SPA pura con Vite)

## Decisions

### Decisión 1: Estructura feature-based vs pages router

**Opción**: Feature-based modules (`features/{name}/{components,hooks,services,types,pages}`)
**Por qué**: El equipo ya definió esta estructura en `docs/ARQUITECTURA.md`. Cada feature es autocontenida con sus componentes, hooks, servicios, tipos y páginas. Coincide con la organización del backend por dominios. Facilita el paralelismo entre features y la eliminación de código muerto cuando una feature se depreca.

### Decisión 2: Manejo de tokens JWT

**Opción**: Almacenar access token en memoria (variable React state) y refresh token en localStorage
**Por qué**: 
- Access token tiene TTL corto (15 min) — almacenarlo en memoria evita exposición XSS prolongada
- Refresh token en localStorage permite persistir la sesión entre refrescos de página sin requerir re-login
- Alternativa considerada: httpOnly cookies. Se descarta porque el frontend y backend pueden estar en dominios distintos en desarrollo (Vite :5173, FastAPI :8000)
- El interceptor de Axios agrega `Authorization: Bearer <token>` automáticamente

### Decisión 3: Refresh transparente con cola de requests

**Opción**: Interceptor que detecta 401, encola requests en vuelo, refresca el token, y replaya las requests encoladas
**Por qué**: Si múltiples requests fallan simultáneamente por token expirado, solo una debe ejecutar el refresh. Las demás deben esperar y reusar el nuevo token. Patrón estándar con TanStack Query + Axios interceptor. Ver diseño en `shared/services/api.ts`.

### Decisión 4: Route guard basado en permisos

**Opción**: Componente `<ProtectedRoute>` que recibe `requiredPermission` como prop, verifica contra el contexto de auth, y redirige a `/login` o muestra 403
**Por qué**: Es declarativo, reutilizable y se alinea con el RBAC del backend. El menú lateral se genera dinámicamente filtrando las rutas disponibles según los permisos del usuario.

### Decisión 5: Enrutamiento con React Router v6

**Opción**: React Router v6 con layout anidado y lazy loading de páginas
**Por qué**: 
- Layout anidado permite sidebar persistente que no se desmonta al navegar entre rutas protegidas
- Lazy loading con `React.lazy` + `Suspense` reduce el bundle inicial
- Las rutas de login/2FA/recovery están fuera del layout protegido

### Decisión 6: TanStack Query para llamado a APIs

**Opción**: Custom hooks en `features/{name}/hooks/` que envuelven llamadas a `shared/services/api.ts` usando TanStack Query para caché, retry y estado de carga
**Por qué**: Evita duplicar lógica de fetching, maneja caché de respuestas, retry automático en errores de red, y provee estado consistente (isLoading, isError, data).

## Risks / Trade-offs

| Riesgo | Mitigación |
|--------|------------|
| [Seguridad] Access token en memoria se pierde al refrescar página, forzando re-login | Usar refresh token en localStorage para recuperar sesión automáticamente sin re-login |
| [UX] Latencia de refresh token en cada expiración | El refresh es transparente para el usuario; el interceptor lo maneja sin interrumpir la interacción |
| [Compatibilidad] CORS entre frontend (Vite :5173) y backend (FastAPI :8000) en desarrollo | Configurar proxy de Vite (`vite.config.ts`) para redirigir `/api/*` al backend. En producción, mismo dominio o CORS configurado en backend |
| [Mantenibilidad] Feature-based puede llevar a duplicación de código entre features tempranas | Extraer lógica compartida a `shared/` apenas se detecte duplicación. No premature-abstract |
