## ADDED Requirements

### Requirement: Gestionar Carreras
El sistema SHALL permitir a los usuarios con permisos de "estructura:gestionar" crear, editar, listar y realizar baja lógica de Carreras. El código de la Carrera MUST ser único por tenant para carreras no eliminadas.

#### Scenario: Creación exitosa de carrera
- **WHEN** un administrador envía datos válidos para crear una carrera (código, nombre, estado "Activa")
- **THEN** la carrera es guardada con su tenant_id, se devuelve un status 201 y la carrera puede ser consultada.

#### Scenario: Fallo por código duplicado
- **WHEN** un administrador intenta crear una carrera con un código ya existente en su tenant (para una carrera no eliminada)
- **THEN** el sistema rechaza la creación y devuelve un error 400.

### Requirement: Gestionar Materias
El sistema SHALL permitir a los usuarios con permisos de "estructura:gestionar" crear, editar, listar y realizar baja lógica de Materias. El código de la Materia MUST ser único por tenant.

#### Scenario: Creación de materia
- **WHEN** un administrador envía datos válidos para crear una materia
- **THEN** la materia se crea asociada a su tenant.

### Requirement: Gestionar Cohortes
El sistema SHALL permitir la gestión de Cohortes vinculadas a Carreras. El nombre de la cohorte MUST ser único para una misma Carrera en un Tenant.

#### Scenario: Validar estado de la Carrera al crear Cohorte
- **WHEN** se intenta crear una Cohorte abierta (vig_hasta es nulo o futuro) asociada a una Carrera con estado "Inactiva"
- **THEN** la operación es rechazada con código 400 por regla de negocio "carrera inactiva no admite cohortes abiertas".

#### Scenario: Unicidad de cohorte en carrera
- **WHEN** se intenta crear una cohorte con un nombre que ya existe en la misma carrera y tenant
- **THEN** se rechaza con error de conflicto 400.
