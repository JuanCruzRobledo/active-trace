## ADDED Requirements

### Requirement: Configurar umbral de aprobación por materia
El sistema SHALL permitir a usuarios con permiso `calificaciones:importar` configurar el umbral de aprobación (`umbral_pct`) y los valores textuales aprobatorios (`valores_aprobatorios`) para una asignación docente específica. El valor por defecto SHALL ser 60% (RN-03).

#### Scenario: Crear umbral con valor personalizado
- **WHEN** un PROFESOR configura un umbral de 75% para su asignación
- **THEN** el sistema persiste el umbral y lo aplica a todas las calificaciones de esa asignación.

#### Scenario: Usar valor por defecto del tenant
- **WHEN** un PROFESOR consulta el umbral de su asignación sin haberlo configurado
- **THEN** el sistema retorna el valor por defecto del tenant (60%).

#### Scenario: Actualizar umbral y recalcular aprobado
- **WHEN** un PROFESOR cambia el umbral de 60% a 80%
- **THEN** el sistema actualiza el umbral y recalcula `aprobado` para todas las calificaciones de esa asignación.

#### Scenario: Umbral con valores aprobatorios textuales personalizados
- **WHEN** un PROFESOR configura `valores_aprobatorios=["Aprobado", "Muy bueno", "Excelente"]`
- **THEN** las calificaciones textuales con esos valores se marcan como `aprobado=True`.

### Requirement: Aislamiento de umbral por asignación
El umbral configurado para una asignación SHALL NO afectar a otras asignaciones, incluso si corresponden a la misma materia (RN-03).

#### Scenario: Umbral por asignación no afecta a otros docentes
- **WHEN** el PROFESOR A configura un umbral de 80% para su asignación en Matemáticas y el PROFESOR B tiene la default de 60% en la misma materia
- **THEN** las calificaciones del PROFESOR A usan 80% y las del PROFESOR B usan 60%.

### Requirement: Consultar umbral
El sistema SHALL permitir a usuarios con permiso `calificaciones:importar` consultar la configuración de umbral actual. PROFESOR solo ve su propia asignación; COORDINADOR/ADMIN ven cualquier asignación del tenant.

#### Scenario: Profesor consulta su propio umbral
- **WHEN** un PROFESOR consulta el umbral de su asignación
- **THEN** el sistema retorna la configuración actual o el default del tenant.

#### Scenario: Profesor no puede ver umbral de otra asignación
- **WHEN** un PROFESOR intenta consultar el umbral de una asignación que no le pertenece
- **THEN** el sistema deniega el acceso (403 Forbidden).

### Requirement: Página de configuración de umbral (frontend)
El sistema SHALL proveer una página donde el PROFESOR configure el porcentaje mínimo de aprobación para una materia.

#### Scenario: Visualizar umbral actual
- **WHEN** el usuario navega a `/comision/:materiaId/umbral`
- **THEN** el sistema muestra el umbral actual de la materia (obtenido de GET `/api/v1/umbral/:materiaId`) con un input numérico para modificarlo, valor por defecto 60%

#### Scenario: Actualizar umbral exitosamente
- **WHEN** el usuario ingresa un nuevo porcentaje (ej: 70) y hace clic en "Guardar"
- **THEN** el sistema envía PUT a `/api/v1/umbral/:materiaId` y muestra mensaje de éxito con el nuevo valor reflejado

#### Scenario: Validación de rango
- **WHEN** el usuario ingresa un valor fuera de rango (menor a 0 o mayor a 100)
- **THEN** el sistema muestra error de validación antes de enviar al backend
