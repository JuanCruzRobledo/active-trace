# Spec: clave-plus-catalogo

## Requirements

### Requirement: Catálogo de claves de Plus configurable por tenant
El sistema SHALL permitir al ADMIN del tenant gestionar el catálogo de claves de Plus que determinan qué plus salarial aplica por materia.

#### Scenario: Crear ClavePlus exitoso
- **WHEN** ADMIN crea una ClavePlus con codigo=PROG, nombre=Programación, activa=true
- **THEN** el sistema retorna la clave creada

#### Scenario: Código único por tenant
- **WHEN** ADMIN intenta crear una ClavePlus con un código ya existente en el mismo tenant
- **THEN** el sistema rechaza con error de conflicto (409)

#### Scenario: Claves aisladas por tenant
- **WHEN** ADMIN del tenant A crea una clave PROG
- **THEN** el tenant B no ve esa clave en su catálogo

#### Scenario: Seed de claves por defecto
- **WHEN** se inicializa un tenant nuevo
- **THEN** el sistema precarga 8 claves: PROG, BD, ING, MAT, RED, WEB, GES, IDI, PRA

#### Scenario: Desactivar ClavePlus
- **WHEN** ADMIN desactiva una ClavePlus (activa=false)
- **THEN** la clave existente no se elimina pero no puede asignarse a nuevas materias

#### Scenario: Asignar clave a materia
- **WHEN** ADMIN asigna una ClavePlus a una Materia mediante `clave_plus_id`
- **THEN** esa materia queda asociada a la clave para efectos de cálculo de liquidación

#### Scenario: Materia sin clave no genera plus
- **WHEN** una Materia tiene `clave_plus_id = null`
- **THEN** esa materia no aporta al cálculo del plus en liquidaciones

#### Scenario: ClavePlus sin permiso
- **WHEN** un rol sin permisos (ej: ALUMNO) intenta gestionar claves
- **THEN** el sistema retorna 403 Forbidden
