# perfil-propio Specification

## Purpose
TBD - created by archiving change c-20-perfil-y-mensajeria-interna. Update Purpose after archive.
## Requirements
### Requirement: Lectura del perfil propio
Todo usuario autenticado SHALL poder consultar su propio perfil vía `GET /api/perfil`. La identidad SHALL derivarse exclusivamente del JWT — ningún parámetro de URL, query o body puede alterar de quién es el perfil. Los campos PII (email, dni, cuil, cbu, alias_cbu) SHALL retornarse enmascarados.

#### Scenario: Usuario consulta su perfil
- **WHEN** un usuario autenticado consulta `GET /api/perfil`
- **THEN** recibe sus propios datos (nombre, apellidos, email enmascarado, regional, banco, cbu enmascarado, alias_cbu enmascarado, facturador, legajo_profesional, cuil enmascarado)

#### Scenario: La identidad viene del JWT
- **WHEN** un usuario autenticado consulta `GET /api/perfil?usuario_id=<otro-uuid>`
- **THEN** el parámetro `usuario_id` se ignora y recibe su propio perfil, no el del otro usuario

#### Scenario: PII enmascarada
- **WHEN** un usuario consulta su perfil
- **THEN** el CUIL y el CBU se devuelven con formato enmascarado (ej. `*****5678-9`), nunca en texto plano

---

### Requirement: Edición del perfil propio
Todo usuario autenticado SHALL poder editar parcialmente su perfil vía `PATCH /api/perfil` sobre los campos editables: nombre, apellidos, email, dni, banco, cbu, alias_cbu, regional, facturador (modalidad de cobro) y legajo_profesional. La operación SHALL aplicarse siempre al usuario del JWT. Toda edición SHALL generar un evento de auditoría `PERFIL_EDITAR`.

#### Scenario: Editar campos editables
- **WHEN** un usuario envía `PATCH /api/perfil` con un nuevo banco y regional
- **THEN** los campos se actualizan, se registra audit log `PERFIL_EDITAR` y la respuesta refleja los nuevos valores (PII enmascarada)

#### Scenario: Edición parcial
- **WHEN** un usuario envía `PATCH /api/perfil` con solo el campo `regional`
- **THEN** solo `regional` cambia y el resto de los campos permanece intacto

#### Scenario: Cambiar modalidad de cobro
- **WHEN** un usuario actualiza `facturador` en su perfil
- **THEN** la modalidad de cobro se actualiza correctamente

---

### Requirement: CUIL de solo lectura
El CUIL (identificador fiscal principal) SHALL ser de solo lectura para el usuario. El schema de edición de perfil NO SHALL aceptar el campo `cuil`; cualquier request que lo incluya SHALL ser rechazado.

#### Scenario: Intento de modificar CUIL
- **WHEN** un usuario envía `PATCH /api/perfil` con un campo `cuil`
- **THEN** el sistema retorna 422 (campo no permitido) y el CUIL no se modifica

#### Scenario: CUIL visible pero no editable
- **WHEN** un usuario consulta su perfil
- **THEN** el CUIL se muestra enmascarado, pero no figura entre los campos que el endpoint de edición acepta

---

### Requirement: Cierre de sesión explícito
Todo usuario autenticado SHALL poder cerrar su sesión de forma explícita, invalidando su sesión activa. Este comportamiento SHALL satisfacerse reutilizando `POST /api/auth/logout` (C-03), que revoca el refresh token del usuario autenticado. NO SHALL introducirse código de logout nuevo en este change.

#### Scenario: Logout revoca la sesión
- **WHEN** un usuario autenticado invoca `POST /api/auth/logout` con su refresh token
- **THEN** el refresh token queda revocado y no puede usarse para obtener nuevos tokens

---

### Requirement: Aislamiento multi-tenant del perfil
Toda operación de perfil SHALL respetar el `tenant_id` del usuario autenticado. Un usuario NO SHALL poder leer ni editar el perfil de un usuario de otro tenant.

#### Scenario: Perfil acotado al tenant
- **WHEN** un usuario del tenant A está autenticado
- **THEN** las operaciones de `/api/perfil` resuelven y modifican únicamente su propio registro dentro del tenant A

