## ADDED Requirements

### Requirement: Página de configuración de umbral
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
