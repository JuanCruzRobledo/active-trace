## Context

activia-trace ya cuenta con estructura académica (C-06: Carrera, Cohorte, Materia) y RBAC con permiso `estructura:gestionar` para COORDINADOR/ADMIN. Los módulos de ProgramaMateria y FechaAcademica completan la gestión académica del coordinador: centralizar los programas oficiales de cada materia (documentos) y calendarizar las instancias evaluativas del período. La salida de contenido para LMS se integra conceptualmente con la funcionalidad existente de generación de bloques HTML (vista en C-13 encuentros F6.4). Los actores involucrados son COORDINADOR y ADMIN (gestión) y PROFESOR/TUTOR/ALUMNO (consulta, en vista futura).

## Goals / Non-Goals

**Goals:**
- Modelar `ProgramaMateria` con asociación a materia × carrera × cohorte, título, referencia de archivo opaca (UUID en storage, no ruta real) y timestamp de carga.
- Proveer API REST para subir un programa (metadatos + referencia a archivo), listar programas por materia/carrera/cohorte, obtener detalle individual y eliminar.
- Modelar `FechaAcademica` con tipo (Parcial, TP, Coloquio, Recuperatorio), número de instancia, período, fecha y título, asociada a materia y cohorte.
- Proveer API REST CRUD para fechas académicas: crear, listar (con filtros por materia, cohorte, tipo, período), obtener, actualizar y eliminar.
- Generar un fragmento de contenido HTML ready para publicar en el aula virtual del LMS a partir de las fechas registradas de una materia+cohorte.
- Auditoría completa de todas las operaciones con códigos específicos.

**Non-Goals:**
- Almacenamiento real de archivos (S3/GCS/filesystem) — La `referencia_archivo` es un UUID interno; el servicio de storage se integra en un change futuro. Por ahora se acepta un valor simbólico.
- Vista de calendario visual en backend (se implementa en frontend C-23).
- Notificaciones al crear/modificar fechas académicas.
- Validación de superposición de fechas entre materias del mismo cohorte.
- Bloqueo de edición de fechas pasadas.
- Integración automática con Moodle (la generación de contenido es un fragmento HTML descargable, no una sync automática).

## Decisions

1. **ProgramaMateria con referencia_archivo como UUID opaco**: No se almacena el archivo real en esta fase. `referencia_archivo` guarda un identificador único (UUID v4) que el frontend/envío usará para referenciar el archivo cuando el servicio de storage esté disponible. La validación de existencia del archivo no se hace a nivel DB — es responsabilidad del servicio de storage futuro.

2. **FechaAcademica con tipo como enum fijo**: Los valores `Parcial`, `TP`, `Coloquio`, `Recuperatorio` cubren el catálogo actual. No se hace configurable porque no hay requerimiento de tipos personalizados por tenant. Si surge, se migra a una tabla `tipo_evaluacion`.

3. **Número de instancia secuencial dentro de (materia, cohorte, tipo)**: El campo `numero` identifica qué instancia es (1er parcial, 2do parcial, etc.). No es auto-generado por el sistema — el usuario lo define al crear. Se valida que no haya duplicados del mismo `(materia_id, cohorte_id, tipo, numero)` dentro del mismo tenant.

4. **Permiso `estructura:gestionar` reutilizado**: Tanto programas como fechas académicas usan el permiso existente `estructura:gestionar` (mapeado a COORDINADOR y ADMIN). No se crean permisos nuevos porque operan sobre la estructura académica. Si en el futuro PROFESOR necesita gestionar fechas, se puede agregar un permiso más fino.

5. **Generación de contenido LMS como endpoint separado**: `GET /api/fechas-academicas/lms-export?materia_id=X&cohorte_id=Y` devuelve texto plano con HTML formateado (tabla de fechas). No se almacena — el usuario copia y pega en el LMS. Esto mantiene la responsabilidad única en cada endpoint.

6. **ProgramaMateria sin soft delete**: Dado que es un documento oficial con referencia a archivo, la eliminación es física (hard delete). El audit log captura `PROGRAMA_ELIMINAR` como trazabilidad. Si se necesita conservar el registro, se migra a soft delete en el futuro.

7. **FechaAcademica con soft delete estándar**: Usa el mixin de soft delete del sistema (C-02). Una fecha eliminada no aparece en listados ni en la exportación LMS, pero se conserva en BD para trazabilidad.

## Risks / Trade-offs

- **[Storage pendiente]** `referencia_archivo` es un placeholder hasta que exista el servicio de storage. **Mitigación**: se diseña el modelo y API con este campo como UUID; cuando el storage exista, solo cambia la implementación del service.
- **[Datos huérfanos]** Si se elimina una Materia o Cohorte (C-06), los programas y fechas asociados quedan huérfanos. **Mitigación**: C-06 no implementa hard delete (soft delete). Al "eliminar" una materia, los programas y fechas asociados se conservan como histórico. No se agrega cascade delete.
- **[Sin vista calendario en backend]** La vista calendario se implementa solo en frontend. **Mitigación**: la API devuelve datos estructurados (fecha, tipo, título) que cualquier calendario JS puede consumir.
- **[Concurrencia en fechas]** Dos coordinadores podrían crear la misma fecha simultáneamente. **Mitigación**: el repository valida unicidad `(materia_id, cohorte_id, tipo, numero)` con unique constraint en DB + manejo de IntegrityError.
