## ADDED Requirements

### Requirement: Scaffolding del proyecto frontend

El sistema SHALL proveer un proyecto React 18 + TypeScript + Vite con la siguiente estructura de directorios:

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── Dockerfile
├── .env.example
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── index.css              # Tailwind directives
    ├── vite-env.d.ts
    └── shared/
        ├── services/
        │   └── api.ts         # Axios centralizado + interceptors
        ├── components/        # UI reutilizable
        │   ├── LoadingSpinner.tsx
        │   └── ErrorMessage.tsx
        └── hooks/
            └── useAuth.ts     # Context + hook de autenticación
```

#### Scenario: Proyecto compila sin errores

- **WHEN** se ejecuta `npm run build` en el directorio `frontend/`
- **THEN** Vite genera los bundles en `frontend/dist/` sin errores de compilación TypeScript

#### Scenario: Dev server responde en puerto configurado

- **WHEN** se ejecuta `npm run dev`
- **THEN** el servidor de Vite inicia en `http://localhost:5173` y responde con el HTML del SPA

### Requirement: Cliente HTTP centralizado con interceptor JWT

El sistema SHALL exponer una instancia de Axios (`shared/services/api.ts`) configurada con:
- `baseURL` desde variable de entorno `VITE_API_URL` (default `/api/v1`)
- Interceptor de request que agrega header `Authorization: Bearer <access_token>` desde el contexto de auth
- Interceptor de response que detecta `401 Unauthorized`
- Mecanismo de **refresh transparente**: al recibir 401, intenta refrescar el token vía `POST /api/auth/refresh`; si el refresh es exitoso, replaya la request original con el nuevo access token; si falla, limpia la sesión y redirige a `/login`
- Cola de requests: si múltiples requests reciben 401 simultáneamente, solo una ejecuta el refresh; las demás esperan y replayan con el nuevo token
- Timeout de 30 segundos por request
- Headers por defecto: `Content-Type: application/json`

#### Scenario: Interceptor agrega token automáticamente

- **WHEN** un usuario autenticado hace una request con `useAuth` proveyendo un access token válido
- **THEN** el interceptor agrega `Authorization: Bearer <access_token>` y la request se completa exitosamente

#### Scenario: Refresh transparente en 401

- **WHEN** un usuario autenticado hace una request y el backend responde 401 (token expirado)
- **THEN** el interceptor ejecuta `POST /api/auth/refresh` con el refresh token guardado, obtiene un nuevo par, replaya la request original, y el usuario no percibe interrupción

#### Scenario: Refresh fallido redirige a login

- **WHEN** un usuario con refresh token inválido/expirado hace una request y el interceptor intenta refrescar
- **THEN** el interceptor falla, limpia tokens del almacenamiento local, lanza evento `auth:logout` y redirige a `/login` sin mostrar error al usuario

#### Scenario: Múltiples requests simultáneas con token expirado

- **WHEN** 3 requests simultáneas reciben 401 por token expirado
- **THEN** solo una ejecuta el refresh; las 2 restantes esperan y replayan con el nuevo token cuando el refresh completa

### Requirement: Layout base con navegación dinámica

El sistema SHALL proveer un layout principal (`App.tsx`) con:
- React Router v6 con rutas anidadas
- Layout protegido con sidebar/menú lateral
- Sidebar dinámico que muestra enlaces según los permisos del usuario (obtenidos del contexto de auth)
- Indicador de usuario logueado (nombre, email, rol) en la cabecera
- Botón de cerrar sesión
- Rutas públicas: `/login`, `/2fa`, `/forgot`, `/reset`
- Rutas protegidas: `/*` (dashboard o redirect a login)
- Página 404 para rutas no encontradas
- Lazy loading de páginas con `React.lazy` + `Suspense`

#### Scenario: Usuario no autenticado ve login

- **WHEN** un usuario sin sesión activa navega a cualquier ruta protegida
- **THEN** el sistema redirige a `/login`

#### Scenario: Sidebar muestra solo permisos del usuario

- **WHEN** un usuario autenticado con rol PROFESOR navega al layout protegido
- **THEN** el sidebar muestra solo las secciones para las que tiene permisos (ej: "Mis Comisiones") y NO muestra secciones de administración

#### Scenario: 404 para rutas inexistentes

- **WHEN** un usuario navega a una ruta que no existe
- **THEN** el sistema muestra una página 404 con un enlace para volver al inicio

### Requirement: Contenedor Docker para frontend

El sistema SHALL incluir un `Dockerfile` multi-stage para el frontend:
- Stage 1 (build): imagen node:20-alpine, instala dependencias, ejecuta `npm run build`
- Stage 2 (serve): imagen nginx:alpine, copia los archivos estáticos de `dist/`, configura nginx para SPA routing (fallback a `index.html`)
- Puerto expuesto: 80

El sistema SHALL agregar un servicio `frontend` al `docker-compose.yml` con:
- Build context: `./frontend`
- Puerto mapeado: `8080:80` (o el configurado)
- Variable de entorno `VITE_API_URL` apuntando al backend

#### Scenario: Docker build del frontend

- **WHEN** se ejecuta `docker build -t trace-frontend ./frontend`
- **THEN** el build multi-stage completa sin errores, generando una imagen con nginx sirviendo la SPA

#### Scenario: docker-compose levanta frontend

- **WHEN** se ejecuta `docker-compose up -d` con el servicio frontend configurado
- **THEN** el contenedor inicia y responde en el puerto configurado con el index.html de la SPA
