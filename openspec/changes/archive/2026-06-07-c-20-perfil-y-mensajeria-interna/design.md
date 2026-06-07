## Context

active-trace ya cuenta con usuarios y asignaciones (C-07), autenticación con logout (C-03) y comunicaciones a alumnos (C-12). Falta el self-service del usuario sobre su propia identidad y un canal de mensajería interna entre usuarios registrados. La Épica 11 (Perfil y Sesión) y el flujo FL-10 (mensajería interna) son el scope. El módulo es de governance BAJO: el usuario opera sobre sus propios datos, sin tocar billing, roles ni auth crítica.

Tres sub-capacidades distintas, con distinto nivel de novedad:
1. **Perfil propio** — reusa el modelo `Usuario` (C-07) y las funciones `mask_*` (C-07 PII); solo agrega un endpoint self-scoped.
2. **Mensajería interna** — modelos nuevos; es lo único con persistencia nueva.
3. **Cierre de sesión** — ya existe `POST /api/auth/logout` (C-03); este change solo lo documenta como reuso, sin código.

## Goals / Non-Goals

**Goals:**
- Exponer `GET /api/perfil` y `PATCH /api/perfil` operando SIEMPRE sobre el usuario del JWT (la identidad jamás viene de la URL ni del body).
- Permitir editar: nombre, apellidos, email, dni, banco, cbu, alias_cbu, regional, facturador (modalidad de cobro), legajo_profesional.
- Garantizar que el **CUIL es de solo lectura**: se devuelve enmascarado pero todo intento de modificarlo se rechaza o se ignora silenciosamente.
- Modelar hilos de mensajes internos entre usuarios registrados con respuesta dentro del hilo.
- Listar solo los hilos donde el usuario autenticado es participante.
- Aislar todo por `tenant_id` y por participación; auditar edición de perfil y envío de mensajes.

**Non-Goals:**
- Edición de perfil de otros usuarios (eso es C-07 `/api/admin/usuarios`, con permiso `usuarios:gestionar`).
- Cambio de contraseña / 2FA desde el perfil (vive en C-03 auth).
- Iniciar nuevos hilos hacia cualquier usuario de forma masiva, adjuntos, o notificaciones push/email (fuera de scope; FL-10 cubre leer y responder).
- Marcar leído/no leído con contadores denormalizados (se puede derivar; ver Decisión 6).
- Modificar el modelo `Comunicacion` (emails a alumnos) — es un canal separado.
- Código nuevo para logout — F11.3 reusa C-03.

## Decisions

1. **Endpoint de perfil self-scoped, identidad desde el JWT.** `/api/perfil` no recibe `usuario_id` en la URL. El `PerfilService` resuelve el `usuario.id` a partir del `ctx.user_id` del JWT (igual patrón que `_resolve_usuario_id` en `tareas.py`: el JWT puede traer `users.id` de auth o directamente `usuario.id`). Esto cumple la "Regla de oro" de FL-01: la identidad sale exclusivamente de la sesión.

2. **CUIL read-only por exclusión en el schema de update.** El `PerfilUpdate` simplemente NO incluye el campo `cuil`. Con `ConfigDict(extra="forbid")` (regla dura), cualquier request que envíe `cuil` recibe 422 automáticamente. El `GET /api/perfil` sí devuelve el CUIL enmascarado vía `mask_cuil`. No se necesita lógica condicional en el service — la imposibilidad de modificarlo es estructural.

3. **Reuso del modelo `Usuario`, no un modelo Perfil nuevo.** El perfil ES el `Usuario`. Se reusa el modelo (C-07) y el cifrado de PII (`EncryptedColumn`). El `PerfilService` es un wrapper delgado sobre la actualización parcial, distinto de `UsuarioService` solo en que (a) se auto-scopea al usuario del JWT y (b) excluye `cuil` y `estado`/`legajo` administrativos del set editable.

4. **Mensajería: modelo de dos tablas `MensajeHilo` + `Mensaje`.** Un `MensajeHilo` agrupa una conversación entre dos usuarios (`usuario_a`, `usuario_b`) con un asunto. Cada `Mensaje` pertenece a un hilo, tiene `autor_id`, `cuerpo` y `creado_at` (append-only, como `ComentarioTarea`). Responder = crear un `Mensaje` nuevo en el hilo. Esto mantiene el modelo simple y las queries de inbox eficientes, espejando el patrón probado Tarea ↔ ComentarioTarea (C-16).

5. **Participación por par de usuarios, no tabla N:M de participantes.** Para el scope de FL-10 (leer hilos recibidos y responder), un hilo entre dos participantes (`usuario_a`/`usuario_b`) cubre el caso. El inbox de un usuario son los hilos donde es `usuario_a` O `usuario_b`. Se evita una tabla `hilo_participante` extra. Si en el futuro se requieren hilos grupales, se migra a N:M sin romper la API.

6. **Sin contador denormalizado de no leídos en la v1.** El estado leído/no leído se modela con un timestamp `leido_at` por mensaje del lado del destinatario, o se omite en la v1 exponiendo solo el orden cronológico. **Decisión v1**: se incluye `leido_at` nullable en `Mensaje` para marcar lectura del destinatario, y el inbox puede derivar "hilos con mensajes no leídos" con un EXISTS. No se almacena contador denormalizado.

7. **Append-only para `Mensaje`.** Igual que `ComentarioTarea`: sin `updated_at` ni `deleted_at`. Un mensaje enviado no se edita ni borra (trazabilidad de la conversación). El hilo sí hereda `BaseMixin` para soft-delete administrativo futuro.

8. **Auditoría de edición de perfil y envío de mensaje.** `PERFIL_EDITAR` registra el set de campos cambiados (sin volcar valores PII en claro — solo nombres de campos). `MENSAJE_ENVIAR` registra `hilo_id` y `mensaje_id`. Se agregan ambos a `VALID_ACCION_CODES`.

9. **Logout sin código nuevo.** F11.3 se satisface con `POST /api/auth/logout` (C-03), que ya revoca el refresh token del usuario autenticado. El spec de `perfil-propio` referencia este comportamiento como requisito cubierto; no se crea ni modifica código de auth. El tasks solo incluye un test de humo que verifica que logout sigue operativo (sin reimplementarlo).

10. **PII enmascarada en todas las respuestas.** `GET /api/perfil` reusa `mask_email/dni/cuil/cbu/alias_cbu` (C-07). El cuerpo de los mensajes no es PII pero el nombre/email del otro participante en el inbox se enmascara igual que en `usuarios.py`.

## Risks / Trade-offs

- **[Hilo de a pares vs grupal]** El modelo de dos participantes limita a conversaciones 1:1. **Mitigación**: cubre FL-10 (leer recibidos + responder). Migración futura a N:M es aditiva.
- **[CUIL read-only por schema]** Si un cliente legacy envía `cuil`, recibe 422 en vez de ignorarlo. **Mitigación**: es el comportamiento deseado y consistente con `extra="forbid"`; documentado en el spec.
- **[Resolución de identidad JWT dual]** El JWT puede traer `users.id` o `usuario.id`. **Mitigación**: se reusa el helper `_resolve_usuario_id` ya probado en C-16, centralizando la lógica.
- **[Aislamiento del inbox]** Un bug en el filtro de participación podría exponer hilos ajenos. **Mitigación**: el repo filtra por `tenant_id` Y por (`usuario_a == actor OR usuario_b == actor`) en TODA query; tests de aislamiento cross-tenant y cross-usuario obligatorios.
- **[Duplicación con UsuarioService]** `PerfilService` repite parte del mapeo de `UsuarioService.actualizar`. **Mitigación**: se acepta la duplicación delgada porque los conjuntos de campos editables difieren (perfil excluye cuil/estado/legajo administrativo) y el scope de identidad es distinto.
