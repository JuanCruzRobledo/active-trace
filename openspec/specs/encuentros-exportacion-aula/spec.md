## ADDED Requirements

### Requirement: Generar bloque HTML para aula virtual (F6.4)

El sistema SHALL generar un bloque HTML autónomo con el calendario de encuentros programados y sus grabaciones, listo para copiar y embeber en el aula virtual del LMS.

#### Scenario: Exportación de encuentros con grabaciones
- **WHEN** un PROFESOR solicita exportar los encuentros de una materia a aula virtual
- **THEN** el sistema genera HTML con: tabla de encuentros (fecha, hora, título, meet_url), los encuentros con video_url se marcan como "Grabación disponible"
- **AND** el HTML usa estilos inline para ser portable

#### Scenario: Exportación sin encuentros
- **WHEN** un PROFESOR solicita exportar encuentros de una materia sin instancias
- **THEN** el sistema retorna HTML con mensaje "No hay encuentros programados"

#### Scenario: Exportación incluye encuentros futuros y pasados con grabación
- **WHEN** se genera el HTML
- **THEN** se incluyen encuentros desde la fecha actual en adelante (futuros)
- **AND** encuentros pasados SOLO si tienen video_url (grabación disponible)
