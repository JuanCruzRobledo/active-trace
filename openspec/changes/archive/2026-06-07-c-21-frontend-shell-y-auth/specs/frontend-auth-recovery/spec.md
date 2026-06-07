## ADDED Requirements

### Requirement: Pantalla de solicitud de recuperación de contraseña

El sistema SHALL mostrar una pantalla (`/forgot`) con:
- Campo de email
- Botón "Enviar enlace de recuperación"
- Mensaje de éxito genérico: "Si el email está registrado, recibirás un enlace para restablecer tu contraseña" (mismo mensaje si el email existe o no — no revelar existencia)
- Manejo de error `429`: "Demasiados intentos. Intenta de nuevo en X segundos"
- Link "Volver al inicio de sesión" → `/login`
- Estado de carga mientras se procesa

#### Scenario: Solicitud de recuperación exitosa

- **WHEN** el usuario ingresa su email y hace clic en "Enviar enlace de recuperación"
- **THEN** el sistema llama a `POST /api/auth/forgot` y muestra "Si el email está registrado, recibirás un enlace para restablecer tu contraseña" independientemente de si el email existe o no

#### Scenario: Rate limit en solicitud de recuperación

- **WHEN** el usuario excede 5 solicitudes en 60s para el mismo email
- **THEN** el sistema muestra "Demasiados intentos. Intenta de nuevo en X segundos"

### Requirement: Pantalla de restablecimiento de contraseña

El sistema SHALL mostrar una pantalla (`/reset?token=<token>`) con:
- Campo de nueva contraseña (con requisitos visibles: mínimo 12 caracteres, 1 mayúscula, 1 minúscula, 1 dígito)
- Campo de confirmación de contraseña
- Botón "Restablecer contraseña"
- Validación en frontend antes de enviar: contraseñas coinciden y cumplen requisitos mínimos
- El token se extrae del query string `?token=`
- Mensajes de error del backend:
  - `400` con "Reset token expired": "El enlace de recuperación expiró. Solicita uno nuevo"
  - `400` con "Reset token already used": "Este enlace ya fue usado. Solicita uno nuevo"
  - `400` con "Invalid reset token": "Enlace inválido. Solicita uno nuevo"
- Mensaje de éxito: "Contraseña actualizada correctamente" + botón "Ir a iniciar sesión" → `/login`
- Estado de carga mientras se procesa
- Si no hay token en la URL, mostrar mensaje: "Enlace inválido. Solicita una nueva recuperación de contraseña"

#### Scenario: Restablecimiento exitoso

- **WHEN** el usuario ingresa una nueva contraseña que cumple los requisitos y coincide en ambos campos, y el token es válido
- **THEN** el sistema llama a `POST /api/auth/reset` con `{ token, new_password }`, muestra "Contraseña actualizada correctamente" con botón para ir a login

#### Scenario: Contraseña no cumple requisitos

- **WHEN** el usuario ingresa una contraseña de menos de 12 caracteres
- **THEN** el sistema muestra validación en frontend antes de enviar: "La contraseña debe tener al menos 12 caracteres, 1 mayúscula, 1 minúscula y 1 dígito"

#### Scenario: Contraseñas no coinciden

- **WHEN** el usuario ingresa contraseñas diferentes en los campos "Nueva contraseña" y "Confirmar contraseña"
- **THEN** el sistema muestra "Las contraseñas no coinciden" antes de enviar

#### Scenario: Token expirado

- **WHEN** el usuario hace clic en un enlace de recuperación con más de 30 minutos de antigüedad
- **THEN** el sistema muestra "El enlace de recuperación expiró. Solicita uno nuevo" con link a `/forgot`

#### Scenario: Reset sin token en URL

- **WHEN** un usuario navega a `/reset` sin parámetro `token`
- **THEN** el sistema muestra "Enlace inválido. Solicita una nueva recuperación de contraseña" con link a `/forgot`
