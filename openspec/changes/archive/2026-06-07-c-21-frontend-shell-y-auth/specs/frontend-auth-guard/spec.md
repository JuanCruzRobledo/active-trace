## ADDED Requirements

### Requirement: Route guard por autenticación

El sistema SHALL proveer un componente `<ProtectedRoute>` que:
- Verifica si el usuario tiene una sesión activa (access token disponible en memoria)
- Si NO hay sesión: redirige a `/login` con `?redirect=<ruta_original>` para poder redirigir de vuelta después del login
- Si hay sesión: renderiza el layout protegido con `<Outlet />` de React Router para las rutas hijas
- Mientras verifica la sesión (restaurando desde refresh token): muestra un spinner de carga

#### Scenario: Usuario no autenticado redirigido a login

- **WHEN** un usuario sin sesión activa intenta acceder a `/comisiones`
- **THEN** el sistema redirige a `/login?redirect=/comisiones`

#### Scenario: Usuario autenticado ve el layout protegido

- **WHEN** un usuario con sesión activa navega a una ruta protegida
- **THEN** el sistema renderiza el layout con sidebar y el contenido de la ruta

#### Scenario: Restauración de sesión muestra spinner

- **WHEN** la aplicación carga y hay un refresh token en localStorage pero no hay access token en memoria
- **THEN** el sistema ejecuta el refresh automático y mientras tanto muestra un spinner de carga (no la página de login)

### Requirement: Route guard por permisos RBAC

El sistema SHALL proveer un componente `<RequirePermission>` (o prop en `<ProtectedRoute>`) que:
- Recibe un permiso requerido en formato `modulo:accion` (ej: `calificaciones:importar`)
- Consulta los permisos del usuario desde `AuthContext`
- Si el usuario NO tiene el permiso: muestra una página de "Acceso denegado" (403) con mensaje "No tenés permisos para acceder a esta sección"
- Si el usuario tiene el permiso: renderiza el contenido

#### Scenario: Usuario sin permiso ve 403

- **WHEN** un usuario con rol TUTOR intenta acceder a una ruta que requiere `liquidaciones:ver`
- **THEN** el sistema muestra "No tenés permisos para acceder a esta sección" sin redirigir a login

#### Scenario: Usuario con permiso ve el contenido

- **WHEN** un usuario con permiso `calificaciones:importar` accede a la ruta de importación
- **THEN** el sistema renderiza el contenido de la ruta normalmente

### Requirement: Menu/sidebar dinámico según permisos

El sistema SHALL generar el menú de navegación del sidebar dinámicamente según los permisos del usuario autenticado. El menú SHALL definir entradas con permiso requerido opcional:
- Si la entrada tiene permiso requerido y el usuario no lo tiene: la entrada NO se muestra
- Si la entrada no tiene permiso requerido: se muestra para cualquier usuario autenticado
- El orden de las entradas es fijo (según configuración)

El menú base SHALL incluir estas secciones (mostradas según permisos):
- Inicio (Dashboard): siempre visible para usuarios autenticados
- Mis Comisiones: `calificaciones:importar` o `atrasados:ver`
- Equipos Docentes: `equipos:asignar`
- Avisos: `avisos:publicar` o `avisos:ver`
- Tareas: `tareas:gestionar` o `tareas:ver`
- Encuentros: `encuentros:gestionar`
- Coloquios: `coloquios:gestionar` o `coloquios:reservar`
- Comunicaciones: `comunicacion:enviar`
- Estructura Académica: `estructura:gestionar`
- Usuarios: `usuarios:gestionar`
- Auditoría: `auditoria:ver`
- Liquidaciones: `liquidaciones:ver`

#### Scenario: ADMIN ve todas las secciones

- **WHEN** un usuario con rol ADMIN (todos los permisos) abre el sidebar
- **THEN** todas las secciones del menú se muestran en orden

#### Scenario: TUTOR ve solo secciones permitidas

- **WHEN** un usuario con rol TUTOR abre el sidebar
- **THEN** solo se muestran "Inicio" y eventualmente "Avisos" (si tiene `avisos:ver`)
- **THEN** NO se muestran "Liquidaciones", "Estructura Académica", "Usuarios", etc.

#### Scenario: PROFESOR ve secciones docentes

- **WHEN** un usuario con rol PROFESOR abre el sidebar
- **THEN** se muestran "Inicio", "Mis Comisiones", "Encuentros", "Avisos" (y otras según su matriz de permisos)
